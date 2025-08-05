# 🌿 GreenThumb — AI-Powered Daily Plant Blog

An **automated AI blog system** built with Django that posts **daily articles** about plants, flowers, fruits, gardening tips, and care guides — powered by **Gemini AI**, **Cloudinary**, and image/video enrichment from **Unsplash** and **YouTube**.

🔗 Live Site: [https://greenthumb-k78v.onrender.com](https://greenthumb-k78v.onrender.com)  
📦 GitHub: [https://github.com/dhruvinvarmora/ai_blog](https://github.com/dhruvinvarmora/ai_blog)

---

## 🚀 Features

- 🧠 **AI-Generated Blog Posts** (Daily via Cron or Manual)
- 🖼️ **HD Images from Unsplash**
- 🎬 **YouTube Video Embeds**
- 📚 **Categorized Content** (Plants, Flowers, Fruits, Gardening, Care)
- 🧾 **Post Details** with Scientific Info & Care Instructions
- 🌐 **SEO-Optimized Pages** with OpenGraph Metadata
- 🖼️ **Plant Photo Gallery** with Lightbox Viewer
- 🧩 **Tags & Categories** for navigation
- ☁️ **Cloud Storage** via Cloudinary
- ⚙️ **Admin Interface** for manual control

---

## 🧠 Tech Stack

| Component        | Tech                          |
|------------------|-------------------------------|
| Backend          | Django 5.2.4                  |
| AI Model         | Gemini 1.5 Pro (Google)       |
| Images           | Unsplash API                  |
| Video Enrichment | YouTube Data API              |
| Cloud Storage    | Cloudinary                    |
| Deployment       | Render.com                    |
| Database         | PostgreSQL                    |
| Styling          | Bootstrap 5                   |

---

## 🛠️ Setup Instructions

### 1. Clone & Install

```bash
git clone https://github.com/dhruvinvarmora/ai_blog.git
cd ai_blog
pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file in the root:

```env
# Django
SECRET_KEY=your-django-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,greenthumb-k78v.onrender.com

# Gemini AI
GEMINI_API_KEY=your-gemini-api-key

# Unsplash (for images)
UNSPLASH_ACCESS_KEY=your-unsplash-api-key

# YouTube (for videos)
YOUTUBE_API_KEY=your-youtube-api-key

# Cloudinary
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret

# Email (optional)
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-password
DEFAULT_FROM_EMAIL=your-email@gmail.com

# PostgreSQL
DB_NAME=your-db-name
DB_USER=your-db-user
DB_PASSWORD=your-db-password
DB_HOST=your-db-host
DB_PORT=5432
```

### 3. Migrate DB & Create Superuser

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

### 4. Run Locally

```bash
python manage.py runserver
```

---

## ⚙️ Management Commands

### Generate a Post
```bash
python manage.py generate_post
```

### Force Generate a Specific Category
```bash
python manage.py generate_post --category plants --force
```

### Automated Daily Post
```bash
python manage.py auto_post_daily
```

### Schedule with Cron
```bash
# Add to crontab
0 9 * * * cd /path/to/project && /path/to/venv/bin/python manage.py auto_post_daily
```

---

## 🖼️ Templates & Pages

- `/` – Homepage
- `/blog/` – All posts
- `/post/<slug>/` – Post detail
- `/gallery/` – Plant gallery
- `/admin/` – Admin interface

---

## 📸 Image & Video Integration

- ✅ HD images from **Unsplash**
- ✅ Embedded videos from **YouTube**
- ✅ Cloud hosting via **Cloudinary**

---

## 🛠️ Customization Tips

- Modify topics in: `blog/management/commands/generate_post.py`
- Add new categories in: `Post.CATEGORY_CHOICES`
- Tweak frontend design via `templates/` directory

---

## 🧪 Testing

```bash
python manage.py test
```

---

## 🧑‍💻 Admin Features

- Add or edit posts manually
- Manage categories/tags
- Bulk delete or update
- View analytics & views

---

## 🧩 Contributing

1. Fork the repo
2. Create a branch: `git checkout -b feature/new-feature`
3. Commit your changes
4. Push and open a PR

---

## 📄 License

MIT License

---

## 📬 Support

Have issues? [Open a GitHub issue](https://github.com/dhruvinvarmora/ai_blog/issues)

---

## 🖼️ Optional: Add Screenshot

> 📸 Add screenshots of homepage, blog, and gallery if you'd like!
> Place them in a `/screenshots` folder and update `README.md` with:
```markdown
![Homepage](screenshots/homepage.png)
![Blog](screenshots/blog.png)
![Gallery](screenshots/gallery.png)
```