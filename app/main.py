import hashlib
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import ForeignKey, LargeBinary, String, create_engine, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

engine = create_engine(os.getenv("DATABASE_URL", "sqlite:///./ciclistas.db"), pool_pre_ping=True)


class Base(DeclarativeBase):
    pass


class Bike(Base):
    __tablename__ = "bikes"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(80))
    category: Mapped[str] = mapped_column(String(30))


class Review(Base):
    __tablename__ = "reviews"
    id: Mapped[int] = mapped_column(primary_key=True)
    bike_id: Mapped[int] = mapped_column(ForeignKey("bikes.id"))
    accessory: Mapped[str] = mapped_column(String(100))
    comment: Mapped[str] = mapped_column(String(1000))
    rating: Mapped[int]
    photo: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    mime: Mapped[str | None] = mapped_column(String(30), nullable=True)


@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="Pedal Club · API de ciclistas", version="1.0.0", lifespan=lifespan)
static = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static), name="static")


class BikeInput(BaseModel):
    owner: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=80)
    category: str = Field(pattern="^(Ruta|Montaña|Gravel|Urbana)$")


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(static / "index.html")


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/ready")
def ready():
    with engine.connect() as conn:
        conn.execute(select(1))
    return {"status": "ready"}


@app.get("/api/bikes")
def bikes():
    with Session(engine) as session:
        return [{"id": b.id, "owner": b.owner, "name": b.name, "category": b.category}
                for b in session.scalars(select(Bike).order_by(Bike.id.desc()))]


@app.post("/api/bikes", status_code=201)
def add_bike(data: BikeInput):
    if not data.owner.strip() or not data.name.strip():
        raise HTTPException(422, "El nombre y el ciclista son obligatorios")
    with Session(engine) as session:
        bike = Bike(**data.model_dump())
        session.add(bike)
        session.commit()
        return {"id": bike.id, **data.model_dump()}


@app.get("/api/reviews")
def reviews():
    with Session(engine) as session:
        rows = session.execute(select(Review, Bike).join(Bike).order_by(Review.id.desc()))
        return [{"id": r.id, "bike_id": b.id, "bike": b.name, "owner": b.owner,
                 "accessory": r.accessory, "comment": r.comment, "rating": r.rating,
                 "photo_url": f"/api/reviews/{r.id}/photo" if r.photo else None} for r, b in rows]


@app.post("/api/reviews", status_code=201)
async def add_review(bike_id: int = Form(...), accessory: str = Form(..., min_length=2, max_length=100),
                     comment: str = Form(..., min_length=3, max_length=1000),
                     rating: int = Form(..., ge=1, le=5), photo: UploadFile | None = File(None)):
    content, mime = None, None
    if not accessory.strip() or not comment.strip():
        raise HTTPException(422, "Completa el accesorio y el comentario")
    if photo and photo.filename:
        content = await photo.read(2 * 1024 * 1024 + 1)
        png = content.startswith(b"\x89PNG\r\n\x1a\n")
        jpeg = content.startswith(b"\xff\xd8\xff")
        if len(content) > 2 * 1024 * 1024 or not (png or jpeg):
            raise HTTPException(422, "La foto debe ser PNG o JPEG, máximo 2 MB")
        mime = "image/png" if png else "image/jpeg"
    with Session(engine) as session:
        if session.get(Bike, bike_id) is None:
            raise HTTPException(404, "Bicicleta no encontrada")
        review = Review(bike_id=bike_id, accessory=accessory, comment=comment,
                        rating=rating, photo=content, mime=mime)
        session.add(review)
        session.commit()
        return {"id": review.id}


@app.get("/api/reviews/{review_id}/photo")
def get_photo(review_id: int):
    with Session(engine) as session:
        review = session.get(Review, review_id)
        if review is None or not review.photo:
            raise HTTPException(404, "Foto no encontrada")
        return Response(review.photo, media_type=review.mime, headers={"X-Content-Type-Options": "nosniff"})


@app.get("/api/stats")
def stats():
    with Session(engine) as session:
        return {"bikes": session.scalar(select(func.count(Bike.id))),
                "reviews": session.scalar(select(func.count(Review.id))),
                "rating": round(session.scalar(select(func.avg(Review.rating))) or 0, 1)}


@app.get("/api/demo/work", include_in_schema=False)
def work():
    if os.getenv("ENABLE_LOAD_TEST", "false").lower() != "true":
        raise HTTPException(404)
    result = hashlib.pbkdf2_hmac("sha256", b"gitops-demo", b"pedal", 120000)
    return {"checksum": result.hex()[:8]}
