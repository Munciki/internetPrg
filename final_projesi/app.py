from flask import Flask, render_template, redirect, session, url_for, request , flash,sessions
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from sqlalchemy import null
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = 'gelistirme_anahtari' #session bilgilerini tarayacıda tutmak icin
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db' # database ne adında olucak
db = SQLAlchemy(app)
 
login_manager = LoginManager(app) #kullanıcı gerekli bir sayfa mevcut ise: kisinin ziyaretini kayıt etsin
login_manager.login_view='login' #gerekli giris icin hangi rota kullanılsın? login rotasına git

class User(UserMixin,db.Model):
     id = db.Column(db.Integer,primary_key=True) # ıdsını alma=tum verileri silme alma cekme islemleri
     name = db.Column(db.String(100), nullable=False) #name-form icindeki degeri al ve gönder
     email = db.Column(db.String(100),unique=True, nullable=False) #email verisi
     password = db.Column(db.String(100), nullable=False) #password verisi
     is_admin = db.Column(db.Integer, nullable=False)
# Ziyaret ile ilişkiyi sadece burada tanımlıyoruz:
     yorumlar = db.relationship('Yorum', back_populates='kullanici')

class Yorum(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    baslik = db.Column(db.String(150), nullable=False)
    icerik = db.Column(db.Text, nullable=False)
    kategori = db.Column(db.String(50), nullable=False)
    tarih = db.Column(db.DateTime, default=datetime.utcnow)  # EKLENDİ
    kullanici_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    kullanici = db.relationship('User', back_populates='yorumlar')




@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))      

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            session['user_id'] = user.id
            session['email'] = user.email
            session['is_admin'] = user.is_admin

            return redirect(url_for('dashboard'))

        flash('E-posta veya şifre hatalı!', 'danger')

    return render_template('login.html')

    # if request.method == 'POST':
     #   email = request.form.get('email')
      #  password = request.form.get('password')
      #  user = User.query.filter_by(email=email).first()

      #  if user and check_password_hash(user.password, password):
       #     login_user(user)    #kullanıcıyı gırıs yapmıs olarak ısaretle.
        #    session['user_id'] = user.id
         #   session['email'] = user.email
          #  session['is_admin'] = user.is_admin
           # return redirect(url_for('dashboard'))  #dashboard a dondur. dashboard ıcınde ılgılı yerde user gırırsı gosterır.
       # flash('E-posta veya şifre hatalı!', 'danger')
   # return render_template('login.html') 

@app.route('/register',methods=['GET','POST']) #register form icinden
def register():
     if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
     if request.method == 'POST': 
         email = request.form.get('email') #regıster formundan gelen emaıl
         password = request.form.get('password') #regıster formundan gelen password
        

         if User.query.filter_by(email=email).first():
            flash('Bu e-posta zaten kayıtlı!', 'danger') #sayfa mesajları dondurme
            return redirect(url_for('register'))
         
         hashed_password = generate_password_hash(password,method='pbkdf2:sha256')
         name = request.form.get('name')
         new_user = User(name=name, email=email,password=hashed_password , is_admin = 0) 
         db.session.add(new_user)
         db.session.commit()

         flash('Kayıt başarılı Giriş yapabilirsiniz', 'success') #sayfa mesajları dondurma
         return redirect(url_for('login'))
     return render_template('register.html')

         


@app.route('/dashboard')
@login_required
def dashboard():
    yorumlar = Yorum.query.filter_by(kullanici_id=current_user.id).order_by(Yorum.id.desc()).all()
    return render_template('dashboard.html', yorumlar=yorumlar)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('index'))


@app.route('/admin')
@login_required
def admin_panel():
    if not session['is_admin']==1:
        flash("Bu sayfaya erişim izniniz yok.", "danger")
        return redirect(url_for('dashboard'))
    return render_template('admin.html')  # Bu kısım eksikti

@app.route('/dashboard/yorum_ekle', methods=['GET', 'POST'])
@login_required
def yorum_ekle():
    if request.method == 'POST':
        baslik = request.form.get('baslik')
        icerik = request.form.get('icerik')
        kategori = request.form.get('kategori')

        if kufur_var_mi(icerik):
            flash("⚠️ Yorumunuzda küfürlü ifadeler tespit edildi. Lütfen temiz bir dil kullanın.", "danger")
            return redirect(url_for('yorum_ekle'))

        yeni_yorum = Yorum(
            baslik=baslik,
            icerik=icerik,
            kategori=kategori,
            kullanici_id=current_user.id
        )
        db.session.add(yeni_yorum)
        db.session.commit()

        flash("✅ Yorum başarıyla kaydedildi!", "success")
        return redirect(url_for('dashboard'))

    return render_template('yorum_ekle.html')


@app.route('/yorum/duzenle/<int:yorum_id>', methods=['GET', 'POST'])
@login_required
def yorum_duzenle(yorum_id):
    yorum = Yorum.query.get_or_404(yorum_id)

    if yorum.kullanici_id != current_user.id:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        yorum.baslik = request.form['baslik']
        yorum.icerik = request.form['icerik']
        yorum.kategori = request.form['kategori']

        db.session.commit()
        return redirect(url_for('dashboard'))
    
    return render_template('yorum_duzenle.html', yorum=yorum)

@app.route('/yorum/sil/<int:yorum_id>', methods=['POST'])
@login_required
def yorum_sil(yorum_id):
    yorum = Yorum.query.get_or_404(yorum_id)


    if yorum.kullanici_id != current_user.id:
        flash("Bu Kaydı Silemezsiniz!", "danger")
        return redirect(url_for('dashboard'))
    
    db.session.delete(yorum)
    db.session.commit()
    flash("Yorum başarıyla silindi!", "success")
    return redirect(url_for('dashboard'))

@app.route('/iletisim')
def iletisim():
    return render_template('iletisim.html')

@app.route('/Destek')
def destek():
    return render_template('Destek.html')

@app.route('/hakkimizda')
def hakkimizda():
    return render_template('hakkimizda.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/yorumlar')
def yorumlar():
    sayfa = request.args.get('sayfa', 1, type=int)
    kategori = request.args.get('kategori', None)

    query = Yorum.query.order_by(Yorum.tarih.desc())

    if kategori:
        query = query.filter_by(kategori=kategori)

    yorumlar = query.paginate(page=sayfa, per_page=5)
    return render_template('yorumlar.html', yorumlar=yorumlar, kategori=kategori)



@app.route('/admin/kullanicilar')
@login_required
def admin_kullanicilar():
    if not current_user.is_admin:
        flash("Yetkisiz erişim!", "danger")
        return redirect(url_for('dashboard'))
    kullanicilar = User.query.all()
    return render_template('admin.html', kullanicilar=kullanicilar)

@app.route('/admin/kullanici_sil/<int:kullanici_id>', methods=['POST'])
@login_required
def kullanici_sil(kullanici_id):
    if not current_user.is_admin:
        flash("Yetkisiz erişim!", "danger")
        return redirect(url_for('dashboard'))
    kullanici = User.query.get_or_404(kullanici_id)
    db.session.delete(kullanici)
    db.session.commit()
    flash("Kullanıcı silindi!", "success")
    return redirect(url_for('admin_kullanicilar'))

@app.route('/admin/yorumlar')
@login_required
def admin_yorumlar():
    if not current_user.is_admin:
        flash("Yetkisiz erişim!", "danger")
        return redirect(url_for('dashboard'))
    yorumlar = Yorum.query.order_by(Yorum.tarih.desc()).all()
    return render_template('admin_yorumlar.html', yorumlar=yorumlar)

@app.route('/admin/yorum_sil/<int:yorum_id>', methods=['POST'])
@login_required
def yorum_sil_admin(yorum_id):
    if not current_user.is_admin:
        flash("Yetkisiz erişim!", "danger")
        return redirect(url_for('dashboard'))
    yorum = Yorum.query.get_or_404(yorum_id)
    db.session.delete(yorum)
    db.session.commit()
    flash("Yorum silindi!", "success")
    return redirect(url_for('admin_yorumlar'))

@app.route('/admin/yorum_duzenle/<int:yorum_id>', methods=['GET', 'POST'])
@login_required
def admin_yorum_duzenle(yorum_id):
    if not current_user.is_admin:
        flash("Yetkisiz erişim!", "danger")
        return redirect(url_for('dashboard'))
    yorum = Yorum.query.get_or_404(yorum_id)

    if request.method == 'POST':
        yorum.icerik = request.form['icerik']
        yorum.kategori = request.form['kategori']
        db.session.commit()
        flash("Yorum başarıyla güncellendi!", "success")
        return redirect(url_for('admin_yorumlar'))

    return render_template('admin_yorum_duzenle.html', yorum=yorum)


def kufur_var_mi(metin):
    try:
        with open('kufurler.txt', 'r', encoding='utf-8') as f:
            kufurler = [line.strip().lower() for line in f.readlines()]
    except FileNotFoundError:
        return False  # Dosya bulunamazsa yorum engellenmesin

    # Yorum metni küçük harfe çevirilir ve noktalama temizlenir
    temiz_metin = re.sub(r'[^\w\s]', '', metin.lower())

    for kufur in kufurler:
        if kufur in temiz_metin:
            return True
    return False

if _name_ == "_main_":
 app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)))
