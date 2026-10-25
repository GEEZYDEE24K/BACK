import asyncio
import json
import logging
from datetime import datetime
from typing import List, Optional, Dict
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from pydantic import BaseModel, Field, field_validator
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.future import select

from backend_estudiantil.adapters.db import (
    MensajeORM, TruequeORM, UserORM, PublicacionORM, MatchORM, get_session_factory
)
from backend_estudiantil.adapters.security.jwt_authenticator import JWTAuthenticator
from backend_estudiantil.config.settings import settings
from backend_estudiantil.infrastructure.security import get_current_user

router = APIRouter(prefix="/trueques", tags=["chat"])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# WebSocket connection manager
# ---------------------------------------------------------------------------

class ConnectionManager:
    def __init__(self):
        # trueque_id -> {WebSocket: {"user_id": int, "user_name": str}}
        self.active_connections: Dict[int, Dict[WebSocket, dict]] = {}
        self._subscriptions: Dict[int, tuple[object, asyncio.Task]] = {}
        self._lock = asyncio.Lock()
        self._redis: Optional[Redis] = None
        self._publisher: Optional[Redis] = None

    async def connect(self, websocket: WebSocket, trueque_id: int, user_id: int, user_name: str):
        await websocket.accept(subprotocol="bearer")
        async with self._lock:
            if trueque_id not in self.active_connections:
                self.active_connections[trueque_id] = {}
            self.active_connections[trueque_id][websocket] = {
                "user_id": user_id,
                "user_name": user_name,
            }
            online_users = list({info["user_id"] for info in self.active_connections[trueque_id].values()})

            if settings.REDIS_URL and trueque_id not in self._subscriptions:
                if self._redis is None:
                    self._redis = Redis.from_url(
                        settings.REDIS_URL, decode_responses=True
                    )
                pubsub = self._redis.pubsub()
                try:
                    await pubsub.subscribe(self._channel(trueque_id))
                except Exception:
                    await pubsub.aclose()
                    if websocket in self.active_connections[trueque_id]:
                        del self.active_connections[trueque_id][websocket]
                    if not self.active_connections[trueque_id]:
                        del self.active_connections[trueque_id]
                    raise
                task = asyncio.create_task(self._listen(trueque_id, pubsub))
                self._subscriptions[trueque_id] = (pubsub, task)

        # Enviar estado actual de la sala al recién conectado
        try:
            await websocket.send_json({
                "type": "room_state",
                "online_users": online_users,
                "current_user_id": user_id,
            })
        except Exception:
            pass

        # Notificar a los demás que el usuario está en línea
        await self.broadcast(
            {
                "type": "presence",
                "user_id": user_id,
                "user_name": user_name,
                "status": "online",
                "online_users": online_users,
            },
            trueque_id,
            exclude_socket=websocket,
        )

    @staticmethod
    def _channel(trueque_id: int) -> str:
        return f"trueque:{trueque_id}:mensajes"

    async def disconnect(self, websocket: WebSocket, trueque_id: int):
        user_info = None
        async with self._lock:
            connections = self.active_connections.get(trueque_id, {})
            if websocket in connections:
                user_info = connections.pop(websocket)
            if not connections:
                self.active_connections.pop(trueque_id, None)
                subscription = self._subscriptions.pop(trueque_id, None)
            else:
                subscription = None

        if subscription:
            pubsub, task = subscription
            if task is not asyncio.current_task():
                task.cancel()
            await pubsub.unsubscribe(self._channel(trueque_id))
            await pubsub.aclose()

        if user_info and trueque_id in self.active_connections:
            uid = user_info["user_id"]
            user_still_connected = any(
                info["user_id"] == uid for info in self.active_connections[trueque_id].values()
            )
            if not user_still_connected:
                online_users = list({info["user_id"] for info in self.active_connections[trueque_id].values()})
                await self.broadcast(
                    {
                        "type": "presence",
                        "user_id": uid,
                        "user_name": user_info["user_name"],
                        "status": "offline",
                        "online_users": online_users,
                    },
                    trueque_id,
                )

    async def _listen(self, trueque_id: int, pubsub):
        try:
            async for event in pubsub.listen():
                if event["type"] == "message":
                    connections = self.active_connections.get(trueque_id, {})
                    for connection in tuple(connections.keys()):
                        try:
                            await connection.send_text(event["data"])
                        except (WebSocketDisconnect, RuntimeError, OSError):
                            await self.disconnect(connection, trueque_id)
        except asyncio.CancelledError:
            raise
        except (RedisError, WebSocketDisconnect, RuntimeError, OSError):
            logger.exception("Error distribuyendo mensajes WebSocket del trueque %s", trueque_id)
            connections = self.active_connections.get(trueque_id, {})
            for connection in tuple(connections.keys()):
                await connection.close(code=1011)
        finally:
            async with self._lock:
                self._subscriptions.pop(trueque_id, None)

    async def broadcast(self, message: dict, trueque_id: int, exclude_socket: Optional[WebSocket] = None):
        if settings.REDIS_URL:
            if self._publisher is None:
                self._publisher = Redis.from_url(settings.REDIS_URL, decode_responses=True)
            await self._publisher.publish(
                self._channel(trueque_id), json.dumps(message, ensure_ascii=False)
            )
            return

        connections = self.active_connections.get(trueque_id, {})
        for connection in tuple(connections.keys()):
            if exclude_socket and connection == exclude_socket:
                continue
            try:
                await connection.send_json(message)
            except (WebSocketDisconnect, RuntimeError, OSError):
                await self.disconnect(connection, trueque_id)


manager = ConnectionManager()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class MensajeCreate(BaseModel):
    contenido: str = Field(..., min_length=1, max_length=2000)

    @field_validator("contenido")
    @classmethod
    def validar_contenido(cls, value: str) -> str:
        contenido = value.strip()
        if not contenido:
            raise ValueError("El mensaje no puede estar vacío")
        return contenido


class MensajeRead(BaseModel):
    id: int
    trueque_id: int
    remitente_id: int
    remitente_nombre: Optional[str] = None
    contenido: str
    fecha_envio: datetime
    realtime_delivery: Optional[str] = None


class TruequeInfoRead(BaseModel):
    """Informacion enriquecida del trueque para el panel de chat."""
    id: int
    estado: str
    usuario_propone_id: int
    usuario_propone_nombre: Optional[str] = None
    usuario_recibe_id: int
    usuario_recibe_nombre: Optional[str] = None
    libro_propone: Optional[str] = None
    libro_recibe: Optional[str] = None
    fecha_propuesta: datetime
    fecha_confirmacion: Optional[datetime] = None
    fecha_completado: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_user_name(session, user_id: int) -> str:
    q = await session.execute(select(UserORM).where(UserORM.id == user_id))
    user = q.scalar_one_or_none()
    if user:
        return f"{user.nombre or ''} {user.apellido or ''}".strip() or f"Usuario #{user_id}"
    return f"Usuario #{user_id}"


async def _get_trueque_or_404(session, trueque_id: int):
    q = await session.execute(select(TruequeORM).where(TruequeORM.id == trueque_id))
    trueque = q.scalar_one_or_none()
    if not trueque:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trueque no encontrado")
    return trueque


def _assert_participant(trueque, user_id: int):
    if user_id not in (trueque.usuario_propone_id, trueque.usuario_recibe_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No eres participante de este trueque")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/{trueque_id}/info",
    response_model=TruequeInfoRead,
    summary="Informacion enriquecida del trueque para el chat",
)
async def obtener_info_trueque(
    trueque_id: int,
    current_user: dict = Depends(get_current_user),
):
    """Retorna informacion completa del trueque incluyendo nombres de participantes y libros."""
    factory = get_session_factory()
    user_id = int(current_user["id"])

    async with factory() as session:
        trueque = await _get_trueque_or_404(session, trueque_id)
        _assert_participant(trueque, user_id)

        nombre_propone = await _get_user_name(session, trueque.usuario_propone_id)
        nombre_recibe = await _get_user_name(session, trueque.usuario_recibe_id)

        # Intentar obtener titulos desde el match asociado
        libro_propone = None
        libro_recibe = None
        if trueque.match_id:
            q_match = await session.execute(select(MatchORM).where(MatchORM.id == trueque.match_id))
            match = q_match.scalar_one_or_none()
            if match:
                q_origen = await session.execute(
                    select(PublicacionORM).where(PublicacionORM.id == match.publicacion_origen_id)
                )
                pub_origen = q_origen.scalar_one_or_none()
                q_destino = await session.execute(
                    select(PublicacionORM).where(PublicacionORM.id == match.publicacion_destino_id)
                )
                pub_destino = q_destino.scalar_one_or_none()
                if pub_origen:
                    libro_propone = pub_origen.titulo
                if pub_destino:
                    libro_recibe = pub_destino.titulo

        return TruequeInfoRead(
            id=trueque.id,
            estado=trueque.estado,
            usuario_propone_id=trueque.usuario_propone_id,
            usuario_propone_nombre=nombre_propone,
            usuario_recibe_id=trueque.usuario_recibe_id,
            usuario_recibe_nombre=nombre_recibe,
            libro_propone=libro_propone,
            libro_recibe=libro_recibe,
            fecha_propuesta=trueque.fecha_propuesta,
            fecha_confirmacion=trueque.fecha_confirmacion,
            fecha_completado=trueque.fecha_completado,
        )


@router.get(
    "/{trueque_id}/mensajes",
    response_model=List[MensajeRead],
    summary="Listar mensajes de chat del trueque",
)
async def listar_mensajes(
    trueque_id: int,
    limit: int = Query(50, ge=1, le=100),
    before_id: Optional[int] = Query(None, gt=0),
    current_user: dict = Depends(get_current_user),
):
    """Retorna una página de mensajes, empezando por los más recientes."""
    factory = get_session_factory()
    user_id = int(current_user["id"])

    async with factory() as session:
        trueque = await _get_trueque_or_404(session, trueque_id)
        _assert_participant(trueque, user_id)

        stmt = (
            select(MensajeORM, UserORM.nombre, UserORM.apellido)
            .outerjoin(UserORM, MensajeORM.remitente_id == UserORM.id)
            .where(
                MensajeORM.trueque_id == trueque_id,
                *([MensajeORM.id < before_id] if before_id is not None else []),
            )
            .order_by(MensajeORM.id.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        rows = reversed(result.all())

        mensajes = []
        for msg, nombre, apellido in rows:
            nombre_completo = (
                f"{nombre or ''} {apellido or ''}".strip() or f"Usuario #{msg.remitente_id}"
            )
            mensajes.append(
                MensajeRead(
                    id=msg.id,
                    trueque_id=msg.trueque_id,
                    remitente_id=msg.remitente_id,
                    remitente_nombre=nombre_completo,
                    contenido=msg.contenido,
                    fecha_envio=msg.fecha_envio,
                )
            )
        return mensajes


@router.post(
    "/{trueque_id}/mensajes",
    response_model=MensajeRead,
    status_code=status.HTTP_201_CREATED,
    summary="Enviar mensaje al chat del trueque",
)
async def enviar_mensaje(
    trueque_id: int,
    payload: MensajeCreate,
    current_user: dict = Depends(get_current_user),
):
    """Envia un nuevo mensaje al chat.

    El chat esta disponible desde el momento de la propuesta (estado 'propuesto'),
    permitiendo que las partes negocien los detalles antes de confirmar el trueque.
    Solo se bloquea cuando el trueque es rechazado.
    """
    contenido = payload.contenido.strip()
    if not contenido:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="El mensaje no puede estar vacio"
        )

    factory = get_session_factory()
    user_id = int(current_user["id"])

    async with factory() as session:
        trueque = await _get_trueque_or_404(session, trueque_id)
        _assert_participant(trueque, user_id)

        if trueque.estado in ("rechazado", "completado"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No puedes enviar mensajes a un trueque rechazado o completado",
            )

        nuevo_mensaje = MensajeORM(
            trueque_id=trueque_id,
            remitente_id=user_id,
            contenido=contenido,
        )
        session.add(nuevo_mensaje)
        await session.commit()
        await session.refresh(nuevo_mensaje)

        nombre_completo = await _get_user_name(session, user_id)

        response_msg = MensajeRead(
            id=nuevo_mensaje.id,
            trueque_id=nuevo_mensaje.trueque_id,
            remitente_id=nuevo_mensaje.remitente_id,
            remitente_nombre=nombre_completo,
            contenido=nuevo_mensaje.contenido,
            fecha_envio=nuevo_mensaje.fecha_envio,
        )

        # Difundir en tiempo real via WebSocket
        msg_dict = response_msg.model_dump()
        msg_dict["fecha_envio"] = msg_dict["fecha_envio"].isoformat()
        msg_dict["type"] = "message"
        try:
            await manager.broadcast(msg_dict, trueque_id)
        except RedisError:
            logger.exception(
                "El mensaje %s se guardó, pero no se pudo distribuir por Redis",
                response_msg.id,
            )
            response_msg.realtime_delivery = "unavailable"

        return response_msg


@router.websocket("/{trueque_id}/ws")
async def websocket_endpoint(websocket: WebSocket, trueque_id: int):
    """Canal WebSocket bidireccional en tiempo real (P2P entre participantes).
    Permite enviar mensajes, indicadores de escritura y presencia activa.
    """
    protocolos = websocket.scope.get("subprotocols", [])
    if len(protocolos) < 2 or protocolos[0] != "bearer":
        await websocket.close(code=4401)
        return

    try:
        payload = JWTAuthenticator().decode_token(protocolos[1])
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        await websocket.close(code=4401)
        return

    factory = get_session_factory()
    user_name = f"Usuario #{user_id}"
    async with factory() as session:
        result = await session.execute(
            select(TruequeORM).where(TruequeORM.id == trueque_id)
        )
        trueque = result.scalar_one_or_none()
        if trueque is None:
            await websocket.close(code=4404)
            return
        result = await session.execute(select(UserORM).where(UserORM.id == user_id))
        user = result.scalar_one_or_none()
        if user is None or user.estado_cuenta != "activo":
            await websocket.close(code=4401)
            return
        if user_id not in (trueque.usuario_propone_id, trueque.usuario_recibe_id):
            await websocket.close(code=4403)
            return
        user_name = f"{user.nombre or ''} {user.apellido or ''}".strip() or f"Usuario #{user_id}"

    try:
        await manager.connect(websocket, trueque_id, user_id, user_name)
    except RedisError:
        logger.exception("No se pudo crear la suscripción Redis para el trueque %s", trueque_id)
        await websocket.close(code=1011)
        return

    try:
        while True:
            text = await websocket.receive_text()
            if not text:
                continue

            try:
                data = json.loads(text)
            except Exception:
                data = {"type": "message", "contenido": text}

            msg_type = data.get("type", "message")

            if msg_type == "typing":
                # Difundir estado de escritura al compañero de intercambio
                is_typing = bool(data.get("is_typing", False))
                await manager.broadcast(
                    {
                        "type": "typing",
                        "trueque_id": trueque_id,
                        "user_id": user_id,
                        "user_name": user_name,
                        "is_typing": is_typing,
                    },
                    trueque_id,
                    exclude_socket=websocket,
                )

            elif msg_type == "message":
                contenido = str(data.get("contenido", "")).strip()
                if not contenido:
                    continue

                async with factory() as session:
                    q = await session.execute(select(TruequeORM).where(TruequeORM.id == trueque_id))
                    t = q.scalar_one_or_none()
                    if not t or t.estado in ("rechazado", "completado"):
                        await websocket.send_json({
                            "type": "error",
                            "detail": "No puedes enviar mensajes a un trueque rechazado o completado",
                        })
                        continue

                    nuevo_msg = MensajeORM(
                        trueque_id=trueque_id,
                        remitente_id=user_id,
                        contenido=contenido,
                    )
                    session.add(nuevo_msg)
                    await session.commit()
                    await session.refresh(nuevo_msg)

                    broadcast_data = {
                        "type": "message",
                        "id": nuevo_msg.id,
                        "trueque_id": nuevo_msg.trueque_id,
                        "remitente_id": nuevo_msg.remitente_id,
                        "remitente_nombre": user_name,
                        "contenido": nuevo_msg.contenido,
                        "fecha_envio": nuevo_msg.fecha_envio.isoformat(),
                    }
                    await manager.broadcast(broadcast_data, trueque_id)

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        await manager.disconnect(websocket, trueque_id)
    except Exception as e:
        logger.exception("Error en WebSocket trueque %s: %s", trueque_id, e)
        await manager.disconnect(websocket, trueque_id)
