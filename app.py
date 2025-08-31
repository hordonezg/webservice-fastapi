# app.py
import os
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

# ------------- Configuración DB -------------
# Puedes usar una variable de entorno DATABASE_URL (Render/Postgres)
# Ejemplo: postgres://user:pass@host:5432/dbname
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dev.db")  # fallback local

# Ajuste para SQLite (check_same_thread)
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dev.db")

# Normalizar prefijo postgres:// -> postgresql+psycopg2://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)


engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# ------------- Modelo (SQLAlchemy) -------------
class Usuario(Base):
    __tablename__ = "usuarios"
    id_usuario = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    correo = Column(String(150), unique=True, nullable=False)
    password = Column(String(100), nullable=False)
    fecha_reg = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# ------------- Esquemas (Pydantic) -------------
class UsuarioIn(BaseModel):
    nombre: str
    correo: EmailStr
    password: str

class UsuarioOut(BaseModel):
    id_usuario: int
    nombre: str
    correo: EmailStr
    fecha_reg: datetime

    class Config:
        from_attributes = True

class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = None
    correo: Optional[EmailStr] = None
    password: Optional[str] = None

# ------------- App -------------
app = FastAPI(title="WebService UMG", version="1.0.0")

# ------------- Endpoints utilitarios -------------
@app.get("/api/health")
def health():
    return {"status": "ok", "service": "webservice-umg", "time": datetime.utcnow().isoformat()}

@app.get("/api/time")
def current_time():
    return {"utc": datetime.utcnow().isoformat()}

# ------------- CRUD Usuarios -------------
@app.post("/api/usuarios", response_model=UsuarioOut, status_code=201)
def crear_usuario(data: UsuarioIn):
    db = SessionLocal()
    try:
        if db.query(Usuario).filter(Usuario.correo == data.correo).first():
            raise HTTPException(status_code=409, detail="El correo ya existe")
        u = Usuario(nombre=data.nombre, correo=data.correo, password=data.password)
        db.add(u)
        db.commit()
        db.refresh(u)
        return u
    finally:
        db.close()

@app.get("/api/usuarios", response_model=List[UsuarioOut])
def listar_usuarios():
    db = SessionLocal()
    try:
        return db.query(Usuario).order_by(Usuario.id_usuario.asc()).all()
    finally:
        db.close()

@app.get("/api/usuarios/{id_usuario}", response_model=UsuarioOut)
def obtener_usuario(id_usuario: int):
    db = SessionLocal()
    try:
        u = db.query(Usuario).get(id_usuario)
        if not u:
            raise HTTPException(status_code=404, detail="No encontrado")
        return u
    finally:
        db.close()

@app.put("/api/usuarios/{id_usuario}", response_model=UsuarioOut)
def actualizar_usuario(id_usuario: int, data: UsuarioUpdate):
    db = SessionLocal()
    try:
        u = db.query(Usuario).get(id_usuario)
        if not u:
            raise HTTPException(status_code=404, detail="No encontrado")
        if data.nombre is not None:
            u.nombre = data.nombre
        if data.correo is not None:
            # validar colisión de correo
            if db.query(Usuario).filter(Usuario.correo == data.correo, Usuario.id_usuario != id_usuario).first():
                raise HTTPException(status_code=409, detail="El correo ya está usado por otro usuario")
            u.correo = data.correo
        if data.password is not None:
            u.password = data.password
        db.commit()
        db.refresh(u)
        return u
    finally:
        db.close()

@app.delete("/api/usuarios/{id_usuario}", status_code=204)
def eliminar_usuario(id_usuario: int):
    db = SessionLocal()
    try:
        u = db.query(Usuario).get(id_usuario)
        if not u:
            raise HTTPException(status_code=404, detail="No encontrado")
        db.delete(u)
        db.commit()
        return
    finally:
        db.close()
