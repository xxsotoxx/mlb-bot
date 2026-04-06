"""
Auth routes for login, setup, user management
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from datetime import timedelta

from app.models.database import get_db, get_all_users, get_user_by_username, create_user, delete_user, count_users, UserDB
from app.auth.security import verify_password, get_password_hash, create_access_token, get_admin_password
from app.auth.deps import get_current_user, require_admin

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ==================== Pydantic Schemas ====================

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict


class UserCreate(BaseModel):
    username: str
    password: str
    is_admin: bool = False


class UserResponse(BaseModel):
    id: int
    username: str
    is_admin: bool
    is_active: bool


class SetupRequest(BaseModel):
    username: str
    password: str


# ==================== HTML Pages ====================

@router.get("/", response_class=HTMLResponse)
async def root_page():
    """Página principal - redirige a login"""
    from fastapi import FastAPI
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/login")


@router.get("/login", response_class=HTMLResponse)
async def login_page(next_url: str = None):
    """Página de login con temática MLB y soporte para next param"""
    """Página de login con temática MLB"""
    from app.models.database import get_db, count_users
    from sqlalchemy.orm import Session
    
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        user_count = count_users(db)
        
        if user_count == 0:
            return """
            <!DOCTYPE html>
            <html lang="es">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>MLB Bot - Configuración Inicial</title>
                <style>
                    * { margin: 0; padding: 0; box-sizing: border-box; }
                    body {
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        background: linear-gradient(135deg, #1a237e 0%, #0d47a1 50%, #1565c0 100%);
                        min-height: 100vh;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                    }
                    .container {
                        background: white;
                        padding: 40px;
                        border-radius: 20px;
                        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                        width: 90%;
                        max-width: 450px;
                    }
                    .logo {
                        text-align: center;
                        margin-bottom: 30px;
                    }
                    .logo h1 {
                        color: #1a237e;
                        font-size: 2.5rem;
                        font-weight: bold;
                    }
                    .logo .mlb-icon {
                        font-size: 4rem;
                        margin-bottom: 10px;
                    }
                    h2 {
                        color: #333;
                        margin-bottom: 25px;
                        text-align: center;
                    }
                    .form-group {
                        margin-bottom: 20px;
                    }
                    label {
                        display: block;
                        margin-bottom: 8px;
                        color: #555;
                        font-weight: 600;
                    }
                    input {
                        width: 100%;
                        padding: 14px;
                        border: 2px solid #e0e0e0;
                        border-radius: 10px;
                        font-size: 1rem;
                        transition: border-color 0.3s;
                    }
                    input:focus {
                        outline: none;
                        border-color: #1565c0;
                    }
                    .btn {
                        width: 100%;
                        padding: 16px;
                        background: linear-gradient(135deg, #c62828 0%, #b71c1c 100%);
                        color: white;
                        border: none;
                        border-radius: 10px;
                        font-size: 1.1rem;
                        font-weight: bold;
                        cursor: pointer;
                        transition: transform 0.2s, box-shadow 0.2s;
                    }
                    .btn:hover {
                        transform: translateY(-2px);
                        box-shadow: 0 5px 20px rgba(198,40,40,0.4);
                    }
                    .note {
                        margin-top: 20px;
                        padding: 15px;
                        background: #fff3e0;
                        border-radius: 10px;
                        font-size: 0.9rem;
                        color: #e65100;
                        text-align: center;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="logo">
                        <div class="mlb-icon">⚾</div>
                        <h1>MLB BOT</h1>
                    </div>
                    <h2>🚀 Configuración Inicial</h2>
                    <form id="setupForm">
                        <div class="form-group">
                            <label for="username">Usuario Administrador</label>
                            <input type="text" id="username" name="username" required placeholder="admin">
                        </div>
                        <div class="form-group">
                            <label for="password">Contraseña</label>
                            <input type="password" id="password" name="password" required placeholder="••••••••">
                        </div>
                        <div class="form-group">
                            <label for="confirm_password">Confirmar Contraseña</label>
                            <input type="password" id="confirm_password" name="confirm_password" required placeholder="••••••••">
                        </div>
                        <button type="submit" class="btn">Crear Administrador</button>
                    </form>
                    <div class="note">
                        ⚠️ Esta es la primera cuenta. Se convertirá en administrador.
                    </div>
                </div>
                <script>
                    document.getElementById('setupForm').addEventListener('submit', async (e) => {
                        e.preventDefault();
                        const username = document.getElementById('username').value;
                        const password = document.getElementById('password').value;
                        const confirm = document.getElementById('confirm_password').value;
                        
                        if (password !== confirm) {
                            alert('Las contraseñas no coinciden');
                            return;
                        }
                        
                        if (password.length < 6) {
                            alert('La contraseña debe tener al menos 6 caracteres');
                            return;
                        }
                        
                        try {
                            const res = await fetch('/api/auth/setup', {
                                method: 'POST',
                                headers: {'Content-Type': 'application/json'},
                                body: JSON.stringify({username, password})
                            });
                            const data = await res.json();
                            
                            if (res.ok) {
                                alert('Administrador creado correctamente. Ahora puedes iniciar sesión.');
                                window.location.href = '/login';
                            } else {
                                alert(data.detail || 'Error al crear administrador');
                            }
                        } catch (err) {
                            alert('Error de conexión');
                        }
                    });
                </script>
            </body>
            </html>
            """
        
        # Login page for existing users
        return """
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>MLB Bot - Iniciar Sesión</title>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #1a237e 0%, #0d47a1 50%, #1565c0 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                .container {
                    background: white;
                    padding: 40px;
                    border-radius: 20px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    width: 90%;
                    max-width: 450px;
                }
                .logo {
                    text-align: center;
                    margin-bottom: 30px;
                }
                .logo h1 {
                    color: #1a237e;
                    font-size: 2.5rem;
                    font-weight: bold;
                }
                .logo .mlb-icon {
                    font-size: 4rem;
                    margin-bottom: 10px;
                }
                .logo .tagline {
                    color: #666;
                    font-size: 1rem;
                    margin-top: 5px;
                }
                h2 {
                    color: #333;
                    margin-bottom: 25px;
                    text-align: center;
                }
                .form-group {
                    margin-bottom: 20px;
                }
                label {
                    display: block;
                    margin-bottom: 8px;
                    color: #555;
                    font-weight: 600;
                }
                input {
                    width: 100%;
                    padding: 14px;
                    border: 2px solid #e0e0e0;
                    border-radius: 10px;
                    font-size: 1rem;
                    transition: border-color 0.3s;
                }
                input:focus {
                    outline: none;
                    border-color: #1565c0;
                }
                .btn {
                    width: 100%;
                    padding: 16px;
                    background: linear-gradient(135deg, #c62828 0%, #b71c1c 100%);
                    color: white;
                    border: none;
                    border-radius: 10px;
                    font-size: 1.1rem;
                    font-weight: bold;
                    cursor: pointer;
                    transition: transform 0.2s, box-shadow 0.2s;
                }
                .btn:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 5px 20px rgba(198,40,40,0.4);
                }
                .error {
                    background: #ffebee;
                    color: #c62828;
                    padding: 12px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                    display: none;
                }
                .forgot {
                    text-align: center;
                    margin-top: 15px;
                }
                .forgot a {
                    color: #1565c0;
                    text-decoration: none;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="logo">
                    <div class="mlb-icon">⚾</div>
                    <h1>MLB BOT</h1>
                    <p class="tagline">Sistema de Predicciones de Apuestas</p>
                </div>
                <h2>Iniciar Sesión</h2>
                <div id="error" class="error"></div>
                <form id="loginForm">
                    <div class="form-group">
                        <label for="username">Usuario</label>
                        <input type="text" id="username" name="username" required placeholder="Ingresa tu usuario">
                    </div>
                    <div class="form-group">
                        <label for="password">Contraseña</label>
                        <input type="password" id="password" name="password" required placeholder="••••••••">
                    </div>
                    <button type="submit" class="btn">Entrar al Sistema</button>
                </form>
                <div class="forgot">
                    <a href="/docs">API Documentation</a>
                </div>
            </div>
            <script>
                document.getElementById('loginForm').addEventListener('submit', async (e) => {
                    e.preventDefault();
                    const username = document.getElementById('username').value;
                    const password = document.getElementById('password').value;
                    const errorDiv = document.getElementById('error');
                    
                    const urlParams = new URLSearchParams(window.location.search);
                    const nextUrl = urlParams.get('next') || '/dashboard';
                    
                    try {
                        const res = await fetch('/api/auth/login', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({username, password})
                        });
                        const data = await res.json();
                        
                        if (res.ok) {
                            // Redirect to set-cookie endpoint which will establish cookie and redirect
                            window.location.href = '/api/auth/set-cookie?token=' + data.access_token + '&next=' + encodeURIComponent(nextUrl);
                        } else {
                            errorDiv.textContent = data.detail || 'Credenciales incorrectas';
                            errorDiv.style.display = 'block';
                        }
                    } catch (err) {
                        errorDiv.textContent = 'Error de conexión';
                        errorDiv.style.display = 'block';
                    }
                });
            </script>
        </body>
        </html>
        """
    finally:
        db.close()


# ==================== API Endpoints ====================

@router.post("/setup", response_model=TokenResponse)
async def setup_admin(setup: SetupRequest, db = Depends(get_db)):
    """
    Configura el primer administrador (solo funciona si no hay usuarios)
    """
    user_count = count_users(db)
    
    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario. Usa el endpoint de login."
        )
    
    if len(setup.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña debe tener al menos 6 caracteres"
        )
    
    password_hash = get_password_hash(setup.password)
    user = create_user(db, setup.username, password_hash, is_admin=True)
    
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "is_admin": user.is_admin
        }
    }


@router.post("/login", response_model=TokenResponse)
async def login(login: LoginRequest, db = Depends(get_db)):
    """
    Inicia sesión y retorna token JWT
    """
    user = get_user_by_username(db, login.username)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario desactivado"
        )
    
    if not verify_password(login.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos"
        )
    
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "is_admin": user.is_admin
        }
    }


@router.get("/me", response_model=UserResponse)
async def get_me(current_user = Depends(get_current_user)):
    """Obtiene información del usuario actual"""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "is_admin": current_user.is_admin,
        "is_active": current_user.is_active
    }


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    current_user: UserDB = Depends(require_admin),
    db = Depends(get_db)
):
    """Lista todos los usuarios (solo admin)"""
    users = get_all_users(db)
    return [
        {
            "id": u.id,
            "username": u.username,
            "is_admin": u.is_admin,
            "is_active": u.is_active
        }
        for u in users
    ]


@router.post("/users", response_model=UserResponse)
async def create_new_user(
    user_data: UserCreate,
    current_user: UserDB = Depends(require_admin),
    db = Depends(get_db)
):
    """Crea un nuevo usuario (solo admin)"""
    existing = get_user_by_username(db, user_data.username)
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario ya existe"
        )
    
    if len(user_data.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña debe tener al menos 6 caracteres"
        )
    
    password_hash = get_password_hash(user_data.password)
    user = create_user(db, user_data.username, password_hash, user_data.is_admin)
    
    return {
        "id": user.id,
        "username": user.username,
        "is_admin": user.is_admin,
        "is_active": user.is_active
    }


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_endpoint(
    user_id: int,
    current_user: UserDB = Depends(require_admin),
    db = Depends(get_db)
):
    """Elimina un usuario (solo admin)"""
    
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes eliminar tu propio usuario"
        )
    
    success = delete_user(db, user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    return None


# ==================== Cookie Management ====================

@router.get("/set-cookie")
async def set_auth_cookie(token: str, next_url: str = "/dashboard"):
    """
    Establece cookie de autenticación y redirige a la página solicitada.
    Este endpoint es usado después del login exitoso.
    """
    from fastapi.responses import RedirectResponse
    
    response = RedirectResponse(url=next_url)
    response.set_cookie(
        key="Authorization",
        value=f"Bearer {token}",
        httponly=True,
        max_age=86400,
        samesite="lax",
        secure=False
    )
    return response


@router.post("/logout")
async def logout():
    """Cierra sesión eliminando la cookie de autenticación"""
    from fastapi.responses import RedirectResponse
    
    response = RedirectResponse(url="/login")
    response.delete_cookie(key="Authorization")
    return response