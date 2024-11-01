from flask import Flask, render_template, request, redirect, url_for, session, redirect, flash
from models import db, Abteilung, Benutzer, Ziele, ZielHistorie
from datetime import datetime
import os
import matplotlib.pyplot as plt


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:root@127.0.0.1/tex10_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['SECRET_KEY'] = os.urandom(24)
db.init_app(app)

def replace_umlaute(text):
    if text:
        text = text.replace('Ä', 'AE').replace('Ö', 'OE').replace('Ü', 'UE')
        text = text.replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue')
    return text

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Überprüfen, ob die Formularfelder existieren und korrekt abgerufen werden
        try:
            name = request.form['name']
            rolle = request.form['rolle']
            abteilungs_id = request.form['abteilungs_id']
            password = request.form['password']
        except KeyError as e:
            flash(f'Ein erforderliches Feld fehlt: {e.args[0]}', 'danger')
            return redirect(url_for('register'))

        # Überprüfen, ob der Benutzername bereits existiert
        existing_user = Benutzer.query.filter_by(name=name).first()
        if existing_user:
            flash('Benutzername bereits vergeben. Bitte wählen Sie einen anderen.', 'danger')
            return redirect(url_for('register'))

        # Neuen Benutzer erstellen und Passwort setzen
        neuer_benutzer = Benutzer(name=name, rolle=rolle, abteilungs_id=abteilungs_id)
        neuer_benutzer.set_password(password)  # Passwort-Hash setzen

        # Benutzer in die Datenbank speichern
        db.session.add(neuer_benutzer)
        db.session.commit()

        flash('Registrierung erfolgreich! Sie können sich nun einloggen.', 'success')
        return redirect(url_for('login'))
    
    # GET-Request: Registrierungformular anzeigen
    return render_template('register.html')

@app.route('/sub_ziel_hinzufuegen/<int:ziel_id>', methods=['GET', 'POST'])
def sub_ziel_hinzufuegen(ziel_id):
    if 'username' not in session:
        flash('Bitte melden Sie sich an, um ein Abteilungs-Ziel hinzuzufügen.', 'danger')
        return redirect(url_for('login'))

    altes_ziel = Ziele.query.get_or_404(ziel_id)
    
    if request.method == 'POST':
        # Move old goal to ZielHistorie
        alte_historie = ZielHistorie(
            abteilungs_id=altes_ziel.abteilungs_id,
            ziel_id=altes_ziel.id,
            aussage=altes_ziel.aussage,
            kriterien=altes_ziel.kriterien,
            bewertung=altes_ziel.bewertung,
            zuletzt_geaendert=altes_ziel.zuletzt_geaendert,
            aenderer=altes_ziel.aenderer,
            anregung=altes_ziel.anregung,
            kommentar=altes_ziel.kommentar
        )
        db.session.add(alte_historie)

        # Update the existing goal with new values instead of creating a new one
        altes_ziel.aussage = request.form['aussage']
        altes_ziel.kriterien = request.form['kriterien']
        altes_ziel.bewertung = request.form['bewertung']
        altes_ziel.aenderer = session['username']
        altes_ziel.anregung = request.form.get('anregung')
        altes_ziel.kommentar = request.form.get('kommentar')
        altes_ziel.zuletzt_geaendert = datetime.utcnow()

        db.session.commit()

        flash('Abteilungs-Ziel erfolgreich hinzugefügt!', 'success')
        return redirect(url_for('index'))

    abteilungen = Abteilung.query.all()
    return render_template('ziel_form.html', ziel=altes_ziel, abteilungen=abteilungen)

@app.route('/dashboard')
def dashboard():
    # Filter-Parameter aus der Anfrage holen
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    selected_abteilungen = request.args.getlist('abteilung')

    # Basis-Abfrage erstellen
    query = ZielHistorie.query

    # Filter anwenden, falls vorhanden
    if start_date:
        query = query.filter(ZielHistorie.zuletzt_geaendert >= start_date)
    if end_date:
        query = query.filter(ZielHistorie.zuletzt_geaendert <= end_date)
    if selected_abteilungen:
        query = query.filter(ZielHistorie.abteilungs_id.in_(selected_abteilungen))

    # Alle Abteilungen für das Dropdown-Menü holen
    abteilungen = Abteilung.query.all()

    # Daten für Chart.js vorbereiten
    historie_data = query.order_by(ZielHistorie.zuletzt_geaendert).all()
    
    # Daten nach Abteilung gruppieren
    dept_data = {}
    for hist in historie_data:
        dept_name = hist.abteilung.name
        if dept_name not in dept_data:
            dept_data[dept_name] = {
                'dates': [],
                'ratings': [],
                # Eindeutige Farbe für jede Abteilung generieren
                'color': f'#{hash(dept_name) % 0xFFFFFF:06x}'
            }
        dept_data[dept_name]['dates'].append(hist.zuletzt_geaendert.strftime('%Y-%m-%d'))
        dept_data[dept_name]['ratings'].append(hist.bewertung)

    # Gesamtscore berechnen
    total_scores = {}
    for dept_name, data in dept_data.items():
        if data['ratings']:
            total_scores[dept_name] = sum(data['ratings']) / len(data['ratings'])
    
    # Gesamtscore zum Chart-Data hinzufügen
    chart_data = {
        'datasets': [
            {
                'label': f"{dept_name} (Ø {total_scores.get(dept_name, 0):.1f})",
                'data': [{'x': date, 'y': rating} 
                        for date, rating in zip(data['dates'], data['ratings'])],
                'borderColor': data['color'],
                'fill': False
            }
            for dept_name, data in dept_data.items()
        ]
    }

    return render_template('dashboard.html', 
                         chart_data=chart_data,
                         abteilungen=abteilungen,
                         total_scores=total_scores)


@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        print(username)

        # Benutzer anhand des Benutzernamens suchen
        benutzer = Benutzer.query.filter_by(name=username).first()
        print("Benutzer:", benutzer)

        # Überprüfen, ob Benutzer existiert und Passwort korrekt ist
        if benutzer and benutzer.check_password(password):
            session['user_id'] = benutzer.id
            session['username'] = benutzer.name
            flash('Erfolgreich eingeloggt!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Ungültige Benutzer-ID oder Passwort', 'danger')
    
    return render_template('login.html')


@app.route('/index')
def index():
    # Suchparameter
    search_query = request.args.get('search', '')
    selected_abteilung = request.args.get('abteilung', '')
    selected_status = request.args.get('status', '')
    
    # Sortier-Parameter
    sort_by = request.args.get('sort', 'id')  # Standardsortierung nach ID
    sort_direction = request.args.get('direction', 'asc')
    
    # Basis-Query
    query = Ziele.query
    
    # Volltextsuche
    if search_query:
        search = f"%{search_query}%"
        query = query.filter(
            db.or_(
                Ziele.aussage.like(search),
                Ziele.kriterien.like(search),
                Ziele.kommentar.like(search)
            )
        )
    
    # Abteilungsfilter
    if selected_abteilung:
        query = query.filter(Ziele.abteilungs_id == selected_abteilung)
    
    # Statusfilter (basierend auf Bewertung)
    if selected_status:
        if selected_status == 'gut':
            query = query.filter(Ziele.bewertung >= 7)
        elif selected_status == 'mittel':
            query = query.filter(Ziele.bewertung.between(4, 6))
        elif selected_status == 'schlecht':
            query = query.filter(Ziele.bewertung <= 3)
    
    # Sortierung anwenden
    if sort_by == 'bewertung':
        order_by = Ziele.bewertung
    elif sort_by == 'datum':
        order_by = Ziele.zuletzt_geaendert
    else:
        order_by = Ziele.id
        
    if sort_direction == 'desc':
        order_by = order_by.desc()
    
    query = query.order_by(order_by)
    
    ziele = query.all()
    abteilungen = Abteilung.query.all()
    
    return render_template('index.html', 
                         ziele=ziele, 
                         abteilungen=abteilungen,
                         search_query=search_query,
                         selected_abteilung=selected_abteilung,
                         selected_status=selected_status,
                         sort_by=sort_by,
                         sort_direction=sort_direction)

@app.route('/ziel/<int:ziel_id>')
def ziel_details(ziel_id):
    sort_by = request.args.get('sort', 'datum')  # Standardsortierung nach Datum
    sort_direction = request.args.get('direction', 'desc')  # Standardrichtung absteigend
    
    ziel = Ziele.query.get_or_404(ziel_id)
    query = ZielHistorie.query.filter_by(ziel_id=ziel_id)
    
    # Sortierung anwenden
    if sort_by == 'bewertung':
        order_by = ZielHistorie.bewertung
    else:  # datum
        order_by = ZielHistorie.zuletzt_geaendert
        
    if sort_direction == 'desc':
        order_by = order_by.desc()
    
    query = query.order_by(order_by)
    historie = query.all()
    
    return render_template('ziel_historie.html', 
                         ziel=ziel, 
                         historie=historie,
                         sort_by=sort_by,
                         sort_direction=sort_direction)

@app.route('/ziel/neu', methods=['GET', 'POST'])
def ziel_neu():
    if request.method == 'POST':
        neues_ziel = Ziele(
            abteilungs_id=request.form['abteilungs_id'],
            aussage=replace_umlaute(request.form['aussage']),
            kriterien=replace_umlaute(request.form['kriterien']),
            bewertung=request.form['bewertung'],
            aenderer=request.form['aenderer'],
            anregung=replace_umlaute(request.form.get('anregung')),
            kommentar=replace_umlaute(request.form.get('kommentar')),
            zuletzt_geaendert=datetime.utcnow()
        )
        db.session.add(neues_ziel)
        db.session.commit()
        return redirect(url_for('index'))
    abteilungen = Abteilung.query.all()
    return render_template('ziel_form.html', abteilungen=abteilungen)

@app.route('/ziel/bearbeiten/<int:ziel_id>', methods=['GET', 'POST'])
def ziel_bearbeiten(ziel_id):
    # Überprüfen, ob der Benutzer eingeloggt ist
    if 'username' not in session:
        flash('Bitte melden Sie sich an, um ein Ziel zu bearbeiten.', 'danger')
        return redirect(url_for('login'))

    # Abrufen des Ziels aus der Datenbank
    ziel = Ziele.query.get_or_404(ziel_id)
    if request.method == 'POST':
        # Aktualisieren der Zielattribute mit den übermittelten Formulardaten
        ziel.abteilungs_id = request.form['abteilungs_id']
        ziel.aussage = replace_umlaute(request.form['aussage'])
        ziel.kriterien = replace_umlaute(request.form['kriterien'])
        ziel.bewertung = int(request.form['bewertung'])
        ziel.aenderer = session['username']  # Der aktuell angemeldete Benutzer
        ziel.anregung = replace_umlaute(request.form.get('anregung'))
        ziel.kommentar = replace_umlaute(request.form.get('kommentar'))
        ziel.zuletzt_geaendert = datetime.utcnow()
        db.session.commit()  # Änderungen in der Datenbank speichern
        flash('Ziel erfolgreich aktualisiert!', 'success')
        return redirect(url_for('index'))
    
    abteilungen = Abteilung.query.all()  # Alle Abteilungen abrufen
    return render_template('ziel_form.html', ziel=ziel, abteilungen=abteilungen)

@app.route('/logout')
def logout():
    # Benutzer aus der Session entfernen
    session.pop('username', None)
    flash('Sie wurden erfolgreich abgemeldet.', 'success')
    return redirect(url_for('login'))

@app.route('/ziel/loeschen/<int:ziel_id>', methods=['POST'])
def ziel_loeschen(ziel_id):
    # Abrufen des Ziels aus der Datenbank
    ziel = Ziele.query.get_or_404(ziel_id)
    db.session.delete(ziel)  # Ziel aus der Datenbank löschen
    db.session.commit()  # Änderungen in der Datenbank speichern
    return redirect(url_for('index'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Alle Datenbanktabellen erstellen
    app.run(debug=True)  # Anwendung im Debug-Modus starten
