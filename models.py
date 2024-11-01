from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# Initialisierung der SQLAlchemy-Datenbank
db = SQLAlchemy()

class Abteilung(db.Model):
    __tablename__ = 'abteilung'
    id = db.Column(db.Integer, primary_key=True)  # Primärschlüssel für die Abteilung
    name = db.Column(db.String(50), nullable=False)  # Name der Abteilung

class Benutzer(db.Model):
    __tablename__ = 'benutzer'
    id = db.Column(db.Integer, primary_key=True)  # Primärschlüssel für den Benutzer
    name = db.Column(db.String(50), nullable=False)  # Name des Benutzers
    rolle = db.Column(db.String(50), nullable=False)  # Rolle des Benutzers
    abteilungs_id = db.Column(db.Integer, db.ForeignKey('abteilung.id'))  # Fremdschlüssel zur Abteilung
    password_hash = db.Column(db.String(256), nullable=False)  # Gehashtes Passwort-Feld

    # Beziehung zur Abteilung
    abteilung = db.relationship('Abteilung', backref='benutzer')

    # Methode zum Setzen des Passworts
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    # Methode zum Überprüfen des Passworts
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Ziele(db.Model):
    __tablename__ = 'ziele'
    id = db.Column(db.Integer, primary_key=True)  # Primärschlüssel für das Ziel
    abteilungs_id = db.Column(db.Integer, db.ForeignKey('abteilung.id'))  # Fremdschlüssel zur Abteilung
    aussage = db.Column(db.String(50), nullable=False)  # Aussage des Ziels
    kriterien = db.Column(db.String(50), nullable=False)  # Kriterien des Ziels
    bewertung = db.Column(db.Integer, nullable=False)  # Bewertung des Ziels
    zuletzt_geaendert = db.Column(db.Date)  # Datum der letzten Änderung
    aenderer = db.Column(db.String(50), nullable=True)  # Benutzer, der zuletzt geändert hat
    anregung = db.Column(db.String(50), nullable=True)  # Anregung zum Ziel
    kommentar = db.Column(db.String(50), nullable=True)  # Kommentar zum Ziel
    
    # Beziehung zur Abteilung
    abteilung = db.relationship('Abteilung', backref='ziele')

class ZielHistorie(db.Model):
    __tablename__ = 'ziele_historie'
    id = db.Column(db.Integer, primary_key=True)
    abteilungs_id = db.Column(db.Integer, db.ForeignKey('abteilung.id'))
    ziel_id = db.Column(db.Integer, db.ForeignKey('ziele.id'))
    aussage = db.Column(db.String(50), nullable=False)
    kriterien = db.Column(db.String(50), nullable=False)
    bewertung = db.Column(db.Integer, nullable=False)
    zuletzt_geaendert = db.Column(db.Date)
    aenderer = db.Column(db.String(50), nullable=True)
    anregung = db.Column(db.String(50), nullable=True)
    kommentar = db.Column(db.String(50), nullable=True)
    
    # Beziehungen
    abteilung = db.relationship('Abteilung', backref='ziel_historie')
    ziel = db.relationship('Ziele', backref='historie')
