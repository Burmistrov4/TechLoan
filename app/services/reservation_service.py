from datetime import datetime, timedelta
from app.config import HORA_APERTURA, HORA_CIERRE, DEFAULT_RESERVATION_MINUTES
from app.database import get_connection


def _a_minutos(hora):
    """Convierte 'HH:MM' en minutos desde medianoche.

    Normaliza formatos como '9:00' y '09:00' al mismo valor, de modo que las
    comparaciones de solapamiento nunca se hagan comparando texto.
    """
    horas, minutos = str(hora).split(":")
    return int(horas) * 60 + int(minutos)


def _a_hora(minutos):
    """Convierte minutos desde medianoche en 'HH:MM'."""
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


class ReservaInvalida(ValueError):
    """Error de validación de una reserva que puede llevar sugerencias.

    ``sugerencias`` es una lista de laboratorios alternativos (dicts) para el
    caso de que el rechazo sea por capacidad insuficiente del laboratorio.
    """

    def __init__(self, mensaje, sugerencias=None):
        super().__init__(mensaje)
        self.sugerencias = sugerencias or []


def _solapa(a_inicio, a_fin, b_inicio, b_fin):
    """¿Se superponen dos intervalos [inicio, fin) dados en minutos?"""
    return a_inicio < b_fin and b_inicio < a_fin


def _weekday_de_fecha(fecha):
    """Día de la semana de una fecha 'AAAA-MM-DD' (0=Lunes..6=Domingo)."""
    return datetime.strptime(fecha, "%Y-%m-%d").weekday()


def _mismo_dia_ocupado(candidata, nueva):
    """¿Pueden caer en el MISMO día calendario dos reservas (ya activas)?

    Reglas (choque cruzado incluido):
    - Puntual vs Puntual: misma ``fecha``.
    - Semestral vs Semestral: mismo ``dia_semana`` **y** mismo ``periodo_academico``.
    - Puntual vs Semestral: la fecha de la puntual cae en el ``dia_semana`` de la
      semestral **y** comparten ``periodo_academico``.
    """
    ct = candidata["tipo_reserva"]
    nt = nueva["tipo_reserva"]

    if ct == "PUNTUAL" and nt == "PUNTUAL":
        return candidata["fecha"] == nueva["fecha"]

    if ct == "SEMESTRAL" and nt == "SEMESTRAL":
        return (candidata["dia_semana"] == nueva["dia_semana"]
                and (candidata["periodo_academico"] or None)
                == (nueva["periodo_academico"] or None))

    # Cruce puntual/semestral.
    if ct == "PUNTUAL":
        puntual, semestral = candidata, nueva
    else:
        puntual, semestral = nueva, candidata
    periodo_p = puntual.get("periodo_academico") or None
    periodo_s = semestral.get("periodo_academico") or None
    if periodo_p and periodo_s and periodo_p == periodo_s:
        try:
            return _weekday_de_fecha(puntual["fecha"]) == semestral["dia_semana"]
        except (ValueError, TypeError):
            return False
    return False


def _bloques_por_defecto():
    """Bloques de 70 min entre HORA_APERTURA y HORA_CIERRE, en minutos."""
    inicio = _a_minutos(HORA_APERTURA)
    cierre = _a_minutos(HORA_CIERRE)
    paso = DEFAULT_RESERVATION_MINUTES
    bloques = []
    t = inicio
    while t + paso <= cierre:
        bloques.append((t, t + paso))
        t += paso
    return bloques


def _bloques_de_edicion(db, edicion_id):
    """Bloques horarios de la edición desde ``edicion_configuracion`` (JSON).

    Clave ``bloques_horarios`` = lista de cadenas «HH:MM-HH:MM». Si no está
    configurada, se usa el conjunto por defecto de 70 minutos.
    """
    from app.services.edicion_service import EdicionService

    try:
        config = EdicionService.obtener_config(edicion_id)
        crudo = (config or {}).get("bloques_horarios")
    except Exception:
        crudo = None
    if not crudo:
        return _bloques_por_defecto()

    import json
    try:
        lista = json.loads(crudo)
        bloques = []
        for tramo in lista:
            ini, fin = str(tramo).split("-")
            bloques.append((_a_minutos(ini), _a_minutos(fin)))
        return bloques or _bloques_por_defecto()
    except (ValueError, TypeError):
        return _bloques_por_defecto()


def obtener_bloques_edicion(edicion_id):
    """API pública: bloques horarios de una edición [(inicio_min, fin_min), ...]."""
    with get_connection() as db:
        return _bloques_de_edicion(db, edicion_id)


class ReservationService:
    @staticmethod
    def calculate_end_time(hora_inicio, duracion_minutos):
        start = datetime.strptime(hora_inicio, "%H:%M")
        end = start + timedelta(minutes=duracion_minutos)
        if end.date() != start.date():
            raise ValueError("La reserva no puede superar las 23:59.")
        return end.strftime("%H:%M")

    @staticmethod
    def has_overlap(laboratorio_id, fecha, hora_inicio, hora_fin):
        with get_connection() as db:
            row = db.execute(
                """SELECT id FROM reservas
                   WHERE laboratorio_id=? AND fecha=?
                     AND estado IN ('CONFIRMADA','ACTIVA')
                     AND hora_inicio < ? AND hora_fin > ? LIMIT 1""",
                (laboratorio_id, fecha, hora_fin, hora_inicio)
            ).fetchone()
        return row is not None

    @staticmethod
    def create_reservation(laboratorio_id, prestatario_id, usuario_sistema_id,
                           fecha, hora_inicio, duracion_minutos, observaciones="",
                           edicion_id=1, tipo_reserva="PUNTUAL", dia_semana=None,
                           periodo_academico=None, seccion_id=None, materia_id=None,
                           cantidad_estudiantes=None):
        if duracion_minutos <= 0 or duracion_minutos > 1440:
            raise ValueError("La duración debe estar entre 1 y 1440 minutos.")

        tipo_reserva = (tipo_reserva or "PUNTUAL").upper()
        if tipo_reserva not in ("PUNTUAL", "SEMESTRAL"):
            raise ValueError("Tipo de reserva inválido.")
        if tipo_reserva == "SEMESTRAL" and dia_semana is None:
            raise ValueError("Una asignación semestral requiere el día de la semana.")

        try:
            datetime.strptime(hora_inicio, "%H:%M")
        except ValueError as exc:
            raise ValueError("Fecha u hora inválida.") from exc

        try:
            selected_date = datetime.strptime(fecha, "%Y-%m-%d").date()
        except (ValueError, TypeError) as exc:
            raise ValueError("Fecha inválida.") from exc

        # Solo las PUNTUALES prohíben el pasado; las SEMESTRALES usan la fecha
        # como referencia de inicio del periodo.
        if tipo_reserva == "PUNTUAL" and selected_date < datetime.now().date():
            raise ValueError("No se puede crear una reserva para una fecha pasada.")

        hora_fin = ReservationService.calculate_end_time(hora_inicio, duracion_minutos)
        ini = _a_minutos(hora_inicio)
        fin = _a_minutos(hora_fin)

        with get_connection() as db:
            lab = db.execute(
                "SELECT estado, capacidad FROM laboratorios WHERE id=?",
                (laboratorio_id,)
            ).fetchone()
            if not lab:
                raise ValueError("El laboratorio no existe.")
            if lab["estado"] != "DISPONIBLE":
                raise ValueError("El laboratorio no está disponible.")

            prestatario = db.execute(
                "SELECT estado, tipo FROM prestatarios WHERE id=?",
                (prestatario_id,)
            ).fetchone()
            if not prestatario:
                raise ValueError("El prestatario no existe.")
            if prestatario["estado"] != "ACTIVO":
                raise ValueError("El prestatario no está activo.")
            # El choque de profesor solo aplica a prestatarios de tipo PROFESOR:
            # es la persona que no puede estar en dos laboratorios a la misma
            # hora. Un estudiante u otro tipo no genera ese conflicto.
            es_profesor = prestatario["tipo"] == "PROFESOR"

            usuario = db.execute(
                "SELECT estado FROM usuarios_sistema WHERE id=?",
                (usuario_sistema_id,)
            ).fetchone()
            if not usuario:
                raise ValueError("El usuario del sistema no existe.")
            if usuario["estado"] != "ACTIVO":
                raise ValueError("El usuario del sistema no está activo.")

            seccion = None
            if seccion_id:
                seccion = db.execute(
                    "SELECT cantidad_estimada FROM secciones WHERE id=?", (seccion_id,)
                ).fetchone()
                if not seccion:
                    raise ValueError("La sección indicada no existe.")

            # --- Validación de capacidad (con laboratorios alternativos) ---
            cantidad = cantidad_estudiantes
            if cantidad in (None, ""):
                cantidad = seccion["cantidad_estimada"] if seccion else None
            if cantidad not in (None, ""):
                cantidad = int(cantidad)
                if cantidad > (lab["capacidad"] or 0):
                    alternativas = [
                        dict(a) for a in db.execute(
                            """SELECT id, codigo, nombre, capacidad FROM laboratorios
                               WHERE edicion_id=? AND estado='DISPONIBLE'
                                 AND capacidad>=? AND id<>?
                               ORDER BY capacidad""",
                            (edicion_id, cantidad, laboratorio_id)
                        ).fetchall()
                    ]
                    raise ReservaInvalida(
                        f"La cantidad de estudiantes ({cantidad}) supera la capacidad "
                        f"del laboratorio ({lab['capacidad']}). Elige un laboratorio "
                        f"con mayor cupo.",
                        sugerencias=alternativas,
                    )

            # --- Choques de laboratorio y de profesor (incl. cruce semestral) ---
            nueva = {
                "tipo_reserva": tipo_reserva,
                "fecha": fecha,
                "dia_semana": dia_semana,
                "periodo_academico": periodo_academico,
            }
            filas = db.execute(
                """SELECT id, laboratorio_id, prestatario_id, fecha, dia_semana,
                          tipo_reserva, periodo_academico, hora_inicio, hora_fin
                   FROM reservas
                   WHERE edicion_id=? AND estado IN ('CONFIRMADA','ACTIVA')""",
                (int(edicion_id),)
            ).fetchall()

            choque_lab = False
            choque_prof = False
            for r in filas:
                candidata = dict(r)
                if not _mismo_dia_ocupado(candidata, nueva):
                    continue
                if not _solapa(ini, fin, _a_minutos(r["hora_inicio"]), _a_minutos(r["hora_fin"])):
                    continue
                if r["laboratorio_id"] == laboratorio_id:
                    choque_lab = True
                elif es_profesor and r["prestatario_id"] == prestatario_id:
                    choque_prof = True

            if choque_lab:
                raise ReservaInvalida(
                    "El laboratorio ya tiene una reserva que se superpone con ese horario."
                )
            if choque_prof:
                raise ReservaInvalida(
                    "El profesor o prestatario ya está asignado a otro laboratorio "
                    "en ese horario."
                )

            cur = db.execute(
                """INSERT INTO reservas
                (edicion_id, laboratorio_id,prestatario_id,usuario_sistema_id,fecha,hora_inicio,
                 hora_fin,duracion_minutos,observaciones,tipo_reserva,dia_semana,
                 periodo_academico,seccion_id,materia_id,cantidad_estudiantes)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (int(edicion_id), laboratorio_id, prestatario_id, usuario_sistema_id, fecha, hora_inicio,
                 hora_fin, duracion_minutos, (observaciones or "").strip() or None,
                 tipo_reserva, dia_semana, (periodo_academico or "").strip() or None,
                 seccion_id, materia_id,
                 int(cantidad) if cantidad not in (None, "") else None)
            )
            return cur.lastrowid

    @staticmethod
    def estado_reserva(edicion_id, laboratorio_id, prestatario_id, tipo_reserva,
                       fecha, dia_semana, periodo_academico, hora_inicio, hora_fin,
                       cantidad_estudiantes=None, excluir_id=None):
        """Evalúa (SIN guardar) si una reserva candidata sería válida.

        Reutiliza la misma semántica de choques que ``create_reservation``
        (``_mismo_dia_ocupado`` / ``_solapa``), de modo que la previsualización en
        vivo, el endpoint de disponibilidad y el guardado nunca discrepan. Pensada
        para la previsualización en vivo y para el visor de disponibilidad.
        """
        tipo_reserva = (tipo_reserva or "PUNTUAL").upper()
        resultado = {
            "disponible": False,
            "laboratorio_disponible": False,
            "choque_laboratorio": False,
            "choque_profesor": False,
            "capacidad_ok": True,
            "motivo": "",
            "sugerencias": [],
        }
        try:
            ini = _a_minutos(hora_inicio)
            fin = _a_minutos(hora_fin)
        except (ValueError, TypeError, AttributeError):
            resultado["motivo"] = "Horas inválidas."
            return resultado

        with get_connection() as db:
            lab = db.execute(
                "SELECT estado, capacidad FROM laboratorios WHERE id=?", (laboratorio_id,)
            ).fetchone()
            if not lab:
                resultado["motivo"] = "El laboratorio no existe."
                return resultado
            resultado["laboratorio_disponible"] = lab["estado"] == "DISPONIBLE"

            prestatario = db.execute(
                "SELECT tipo FROM prestatarios WHERE id=?", (prestatario_id,)
            ).fetchone()
            es_profesor = bool(prestatario) and prestatario["tipo"] == "PROFESOR"

            # Capacidad.
            if cantidad_estudiantes not in (None, ""):
                cantidad = int(cantidad_estudiantes)
                if cantidad > (lab["capacidad"] or 0):
                    resultado["capacidad_ok"] = False
                    resultado["sugerencias"] = [
                        dict(a) for a in db.execute(
                            """SELECT id, codigo, nombre, capacidad FROM laboratorios
                               WHERE edicion_id=? AND estado='DISPONIBLE'
                                 AND capacidad>=? AND id<>?
                               ORDER BY capacidad""",
                            (edicion_id, cantidad, laboratorio_id)
                        ).fetchall()
                    ]

            # Choques de laboratorio y de profesor.
            nueva = {
                "tipo_reserva": tipo_reserva,
                "fecha": fecha,
                "dia_semana": dia_semana,
                "periodo_academico": periodo_academico,
            }
            filas = db.execute(
                """SELECT laboratorio_id, prestatario_id, fecha, dia_semana, tipo_reserva,
                          periodo_academico, hora_inicio, hora_fin
                   FROM reservas
                   WHERE edicion_id=? AND estado IN ('CONFIRMADA','ACTIVA') AND id<>?""",
                (int(edicion_id), excluir_id or 0)
            ).fetchall()
            for r in filas:
                if not _mismo_dia_ocupado(dict(r), nueva):
                    continue
                if not _solapa(ini, fin, _a_minutos(r["hora_inicio"]), _a_minutos(r["hora_fin"])):
                    continue
                if r["laboratorio_id"] == laboratorio_id:
                    resultado["choque_laboratorio"] = True
                elif es_profesor and r["prestatario_id"] == prestatario_id:
                    resultado["choque_profesor"] = True

        motivos = []
        if not resultado["laboratorio_disponible"]:
            motivos.append("el laboratorio no está disponible")
        if resultado["choque_laboratorio"]:
            motivos.append("el laboratorio ya tiene una clase en ese horario")
        if resultado["choque_profesor"]:
            motivos.append("el profesor ya está asignado a otro laboratorio en ese horario")
        if not resultado["capacidad_ok"]:
            motivos.append("la cantidad de estudiantes supera la capacidad del laboratorio")

        resultado["motivo"] = "Conflicto: " + "; ".join(motivos) + "." if motivos else "Disponible."
        resultado["disponible"] = not motivos
        return resultado

    @staticmethod
    def cancel(reservation_id):
        """Marca una reserva como CANCELADA.

        Una reserva cancelada deja de bloquear la franja horaria: la regla de
        solapamiento solo considera los estados CONFIRMADA y ACTIVA.
        """
        with get_connection() as db:
            row = db.execute(
                "SELECT estado FROM reservas WHERE id=?", (reservation_id,)
            ).fetchone()
            if not row:
                raise ValueError("La reserva no existe.")
            if row["estado"] in ("CANCELADA", "FINALIZADA"):
                raise ValueError("La reserva ya no puede cancelarse.")
            db.execute(
                "UPDATE reservas SET estado='CANCELADA' WHERE id=?", (reservation_id,)
            )

    @staticmethod
    def get(reservation_id):
        """Devuelve una reserva con sus datos relacionados (para el comprobante)."""
        with get_connection() as db:
            fila = db.execute(
                """SELECT r.*,
                          l.codigo AS laboratorio_codigo,
                          l.nombre AS laboratorio_nombre,
                          l.ubicacion AS laboratorio_ubicacion,
                          p.cedula, p.nombre AS prestatario_nombre,
                          p.apellido AS prestatario_apellido,
                          p.email AS prestatario_email,
                          p.telefono AS prestatario_telefono,
                          u.username AS registrado_por,
                          u.nombre || ' ' || u.apellido AS registrado_por_nombre
                   FROM reservas r
                   JOIN laboratorios l ON l.id = r.laboratorio_id
                   JOIN prestatarios p ON p.id = r.prestatario_id
                   JOIN usuarios_sistema u ON u.id = r.usuario_sistema_id
                   WHERE r.id = ?""",
                (reservation_id,),
            ).fetchone()
        return dict(fila) if fila else None

    @staticmethod
    def ocupacion_del_dia(laboratorio_id, fecha):
        """Franjas ya ocupadas de un laboratorio en una fecha concreta.

        Se usa para dibujar la línea de tiempo del día en el formulario de
        reservas: el usuario ve de un vistazo qué queda libre.
        """
        with get_connection() as db:
            filas = db.execute(
                """SELECT hora_inicio, hora_fin, estado FROM reservas
                   WHERE laboratorio_id = ? AND fecha = ?
                     AND estado IN ('CONFIRMADA','ACTIVA')
                   ORDER BY hora_inicio""",
                (laboratorio_id, fecha),
            ).fetchall()
        return [dict(fila) for fila in filas]

    @staticmethod
    def sugerir_horarios(laboratorio_id, fecha, duracion_minutos, hora_deseada=None, limite=3):
        """Propone las franjas libres más cercanas a la hora solicitada.

        Es la parte "inteligente" del módulo de reservas: en lugar de limitarse a
        rechazar un solapamiento, calcula los huecos reales del día y ofrece
        alternativas ordenadas por cercanía a lo que el usuario pedía.
        """
        if not fecha or not duracion_minutos or duracion_minutos <= 0:
            return []

        apertura = _a_minutos(HORA_APERTURA)
        cierre = _a_minutos(HORA_CIERRE)

        ocupadas = sorted(
            (_a_minutos(r["hora_inicio"]), _a_minutos(r["hora_fin"]))
            for r in ReservationService.ocupacion_del_dia(laboratorio_id, fecha)
        )

        # Unir intervalos que se tocan o se superponen para obtener los bloques
        # realmente ocupados (las franjas adyacentes cuentan como un solo bloque).
        bloques = []
        for inicio, fin in ocupadas:
            if bloques and inicio <= bloques[-1][1]:
                bloques[-1] = (bloques[-1][0], max(bloques[-1][1], fin))
            else:
                bloques.append((inicio, fin))

        # Huecos libres dentro del horario de apertura.
        huecos = []
        cursor = apertura
        for inicio, fin in bloques:
            if inicio - cursor >= duracion_minutos:
                huecos.append((cursor, inicio))
            cursor = max(cursor, fin)
        if cierre - cursor >= duracion_minutos:
            huecos.append((cursor, cierre))

        deseada = _a_minutos(hora_deseada) if hora_deseada else None

        sugerencias = []
        for inicio, fin in huecos:
            propuesta = inicio
            if deseada is not None and inicio <= deseada and deseada + duracion_minutos <= fin:
                propuesta = deseada
            referencia = deseada if deseada is not None else apertura
            sugerencias.append(
                {
                    "hora_inicio": _a_hora(propuesta),
                    "hora_fin": _a_hora(propuesta + duracion_minutos),
                    # Hasta cuándo sigue libre el hueco: es más útil para el
                    # usuario que un número de minutos suelto.
                    "libre_hasta": _a_hora(fin),
                    "holgura_minutos": fin - inicio,
                    "_distancia": abs(propuesta - referencia),
                }
            )

        sugerencias.sort(key=lambda s: s["_distancia"])
        for sugerencia in sugerencias:
            sugerencia.pop("_distancia", None)
        return sugerencias[:limite]

    @staticmethod
    def proximas_reservas_por_laboratorio(dias=7):
        """Situación de cada laboratorio, indexada por id.

        Responde a lo que el listado de laboratorios no decía: si un laboratorio
        está libre ahora, ¿hasta cuándo? Y si está ocupado, ¿hasta qué hora?

        Devuelve, por laboratorio, la **próxima reserva** que empieza o está en
        curso (con ``es_hoy`` y ``en_curso`` ya calculados) y cuántas reservas
        tiene en los próximos ``dias``, que es la señal de saturación.
        """
        ahora = datetime.now()
        hoy = ahora.strftime("%Y-%m-%d")
        hora_actual = ahora.strftime("%H:%M")
        hasta = (ahora + timedelta(days=dias)).strftime("%Y-%m-%d")

        with get_connection() as db:
            proximas = db.execute(
                """SELECT r.laboratorio_id, r.fecha, r.hora_inicio, r.hora_fin,
                          p.nombre || ' ' || p.apellido AS prestatario
                     FROM reservas r
                     JOIN prestatarios p ON p.id = r.prestatario_id
                    WHERE r.estado IN ('CONFIRMADA', 'ACTIVA')
                      AND r.fecha >= ?
                      -- Las de hoy ya terminadas no cuentan como "próximas".
                      AND NOT (r.fecha = ? AND r.hora_fin <= ?)
                    ORDER BY r.fecha, r.hora_inicio""",
                (hoy, hoy, hora_actual),
            ).fetchall()

            demanda = db.execute(
                """SELECT laboratorio_id, COUNT(*) AS total
                     FROM reservas
                    WHERE estado IN ('CONFIRMADA', 'ACTIVA')
                      AND fecha BETWEEN ? AND ?
                    GROUP BY laboratorio_id""",
                (hoy, hasta),
            ).fetchall()

        resultado = {
            fila["laboratorio_id"]: {"total_semana": fila["total"]} for fila in demanda
        }

        for fila in proximas:
            laboratorio_id = fila["laboratorio_id"]
            dato = resultado.setdefault(laboratorio_id, {"total_semana": 0})
            if "fecha" in dato:
                continue  # ya se guardó la más próxima (vienen ordenadas)
            dato.update(
                {
                    "fecha": fila["fecha"],
                    "hora_inicio": fila["hora_inicio"],
                    "hora_fin": fila["hora_fin"],
                    "prestatario": fila["prestatario"],
                    "es_hoy": fila["fecha"] == hoy,
                    "en_curso": fila["fecha"] == hoy
                    and fila["hora_inicio"] <= hora_actual < fila["hora_fin"],
                }
            )

        return resultado

    @staticmethod
    def list_all():
        with get_connection() as db:
            return [dict(r) for r in db.execute(
                """SELECT r.*, l.codigo AS laboratorio_codigo, l.nombre AS laboratorio_nombre,
                   p.cedula, p.nombre AS prestatario_nombre, p.apellido AS prestatario_apellido
                   FROM reservas r
                   JOIN laboratorios l ON l.id=r.laboratorio_id
                   JOIN prestatarios p ON p.id=r.prestatario_id
                   ORDER BY r.fecha DESC, r.hora_inicio DESC"""
            ).fetchall()]
