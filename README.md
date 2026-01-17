**ExamBot** — bu Telegram bot va Web admin panel orqali test/imtihonlarni boshqarish tizimi. Loyihada **Docker**, **Django**, va **PostgreSQL** ishlatilgan.

**Projectni ishlatish** - docker qoshilganligi uchun projectni ishlatish uchun shunchaki **docker compose up --build** commandni ozi yetadi

**Admin panelga kirish uchun user yaratish** -- docker exec -it exambot_web python manage.py createsuperuser

**Imtihon qoshish** - admin panelda exam qoshish uchun exam nomi va uni soni va ichida test savollari bolgan excel file kerak
excel file korinishi :
    Questions | Version A |  Version B | Version C | Version D | Correct answer

