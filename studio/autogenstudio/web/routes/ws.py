# api/ws.py
import asyncio
import json
from datetime import datetime

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState
from loguru import logger

from ...datamodel import Run, RunStatus, Team
from ...utils.utils import construct_task
from ..auth.dependencies import get_ws_auth_manager
from ..auth.wsauth import WebSocketAuthHandler
from ..deps import get_db, get_websocket_manager
from ..managers.connection import WebSocketManager

router = APIRouter()


@router.websocket("/runs/{run_id}")
async def run_websocket(
    websocket: WebSocket,
    run_id: int,
    ws_manager: WebSocketManager = Depends(get_websocket_manager),
    db=Depends(get_db),
    auth_manager=Depends(get_ws_auth_manager),
):
    """
    WebSocket endpoint for real-time task execution communication.
    
    ## Connection
    - **URL**: `ws://localhost:8084/ws/runs/{run_id}`
    - **Authentication**: Optional Bearer token in query: `?token=your_token`
    - **Protocol**: WebSocket (RFC 6455)
    
    ## Parameters
    - **run_id** (int): The ID of the run to connect to
    
    ## Client Messages (JSON)
    - **start**: Begin task execution
        ```json
        {
            "type": "start",
            "task": "Task description",
            "files": [],
            "team_config": {}
        }
        ```
    - **stop**: Stop execution
        ```json
        {
            "type": "stop", 
            "reason": "User cancelled"
        }
        ```
    - **ping**: Connection check
        ```json
        {"type": "ping"}
        ```
    - **input_response**: Respond to agent input request
        ```json
        {
            "type": "input_response",
            "response": "User input"
        }
        ```
    
    ## Server Messages (JSON)
    - **system**: Connection status
    - **message**: Agent messages during execution
    - **message_chunk**: Streaming content chunks
    - **result**: Final task result
    - **input_request**: Request for user input
    - **error**: Error messages
    - **pong**: Response to ping
    
    ## Error Codes
    - **4001**: Authentication failed
    - **4003**: Not authorized or invalid run state
    - **4004**: Run not found
    """

    try:
        logger.info(f"WebSocket connection attempt for run {run_id}")
        
        # Verify run exists before connecting
        try:
            run_response = db.get(Run, filters={"id": run_id}, return_json=False)
            if not run_response.status or not run_response.data:
                logger.warning(f"Run {run_id} not found in database")
                await websocket.close(code=4004, reason="Run not found")
                return
        except Exception as e:
            logger.error(f"Database error when checking run {run_id}: {str(e)}")
            await websocket.close(code=4004, reason="Database error")
            return

        run = run_response.data[0]
        logger.info(f"Found run {run_id} with status {run.status}")

        if run.status not in [RunStatus.CREATED, RunStatus.ACTIVE, RunStatus.STOPPED]:
            logger.warning(f"Run {run_id} in invalid state: {run.status}")
            await websocket.close(code=4003, reason="Run not in valid state")
            return

        # Connect websocket (this handles acceptance internally)
        try:
            connected = await ws_manager.connect(websocket, run_id)
            if not connected:
                logger.error(f"Failed to connect WebSocket for run {run_id}")
                return  # No need to close here as connect() failure would have closed it
        except Exception as e:
            logger.error(f"WebSocket manager connection error for run {run_id}: {str(e)}")
            return

        # Handle authentication if enabled
        if auth_manager is not None and auth_manager.config.type != "none":
            try:
                ws_auth = WebSocketAuthHandler(auth_manager)
                success, user = await ws_auth.authenticate(websocket)
                if not success:
                    logger.warning(f"Authentication failed for WebSocket connection to run {run_id}")
                    await websocket.send_json(
                        {
                            "type": "error",
                            "error": "Authentication failed",
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )
                    return

                if user and run.user_id != user.id and "admin" not in (user.roles or []):
                    await websocket.send_json(
                        {
                            "type": "error",
                            "error": "Authentication failed",
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )
                    logger.warning(f"User {user.id} not authorized to access run {run_id}")
                    return
                    
                logger.info(f"WebSocket authentication successful for run {run_id}, user: {user.id if user else 'unknown'}")
            except Exception as e:
                logger.error(f"Authentication error for run {run_id}: {str(e)}")
                await websocket.send_json(
                    {
                        "type": "error",
                        "error": "Authentication error",
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
                return
        else:
            logger.info(f"Authentication disabled for WebSocket connection to run {run_id} (type: {auth_manager.config.type if auth_manager else 'none'})")

        logger.info(f"WebSocket connection established for run {run_id}")

        # Send connection success message
        await websocket.send_json(
            {
                "type": "system",
                "status": "ready",
                "message": "WebSocket connection ready for communication",
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        raw_message = None  # Initialize to avoid possibly unbound variable
        while True:
            try:
                # Check if websocket is still connected
                if websocket.client_state == WebSocketState.DISCONNECTED:
                    logger.info(f"WebSocket disconnected for run {run_id}")
                    break
                    
                raw_message = await websocket.receive_text()
                message = json.loads(raw_message)

                if message.get("type") == "start":
                    # Handle start message
                    logger.info(f"Received start request for run {run_id}")
                    task = construct_task(query=message.get("task"), files=message.get("files"))

                    team_config = message.get("team_config")
                    # team_config 支持两种模式
                    # 1. team_config 中包含id字段， 则为 TeamConfig 类型， 通过id 到数据库中查询 Team 配置
                    # 2. 如果 team_config 是一个完整的 AutoGen的Team 或者Solution 对象，则直接使用
                    if task and team_config:
                        # Start the stream in a separate task
                        if isinstance(team_config, dict) and "id" in team_config:
                            # 这种模式，team 团队是预置的， 通过id查询数据库获取Team
                            team_response = db.get(Team, filters={"id": team_config["id"]}, return_json=True)

                            if team_response.status and team_response.data:
                                team = team_response.data[0]
                                # 使用数据库中的team配置
                                asyncio.create_task(ws_manager.start_stream(run_id, task, team["component"]))
                            else:
                                logger.error(f"Team with id {team_config['id']} not found")
                                await websocket.send_json(
                                    {
                                        "type": "error",
                                        "error": f"Team with id {team_config['id']} not found",
                                        "timestamp": datetime.utcnow().isoformat(),
                                    }
                                )
                        else: 
                            # 原始autogenstudio 兼容，外部直接传入 ComponentModel 的dict
                            asyncio.create_task(ws_manager.start_stream(run_id, task, team_config))
                    else:
                        logger.warning(f"Invalid start message format for run {run_id}")
                        await websocket.send_json(
                            {
                                "type": "error",
                                "error": "Invalid start message format",
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        )

                elif message.get("type") == "stop":
                    logger.info(f"Received stop request for run {run_id}")
                    reason = message.get("reason") or "User requested stop/cancellation"
                    await ws_manager.stop_run(run_id, reason=reason)

                elif message.get("type") == "ping":
                    logger.info(f"Received ping from run {run_id}")
                    await websocket.send_json({"type": "pong", "timestamp": datetime.utcnow().isoformat()})
                    logger.info(f"Sent pong to run {run_id}")

                elif message.get("type") == "input_response":
                    # Handle input response from client
                    response = message.get("response")
                    if response is not None:
                        await ws_manager.handle_input_response(run_id, response)
                    else:
                        logger.warning(f"Invalid input response format for run {run_id}")

            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received for run {run_id}: {raw_message}")
                await websocket.send_json(
                    {"type": "error", "error": "Invalid message format", "timestamp": datetime.utcnow().isoformat()}
                )

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for run {run_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        await ws_manager.disconnect(run_id)
