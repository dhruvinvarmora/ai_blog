from django.urls import path
from .views import (
    PostListView, PostDetailView, AboutView, GalleryView, BlogView, ContactView,
    CategoryPostListView, TagPostListView, SearchPostListView,GeneratePostView
)

app_name = 'blog'
urlpatterns = [
    path('', PostListView.as_view(), name='home'),
    path('about/', AboutView.as_view(), name='about'),
    path('gallery/', GalleryView.as_view(), name='gallery'),
    path('blog/', BlogView.as_view(), name='blog'),
    path('contact/', ContactView.as_view(), name='contact'),
    path('post/<slug:slug>/', PostDetailView.as_view(), name='post_detail'),
    path('category/<slug:category_slug>/', CategoryPostListView.as_view(), name='category_posts'),
    path('tag/<slug:tag_slug>/', TagPostListView.as_view(), name='tag_posts'),
    path('search/', SearchPostListView.as_view(), name='search'),
    path('superadmin/generate-post/', GeneratePostView.as_view(), name='admin_generate_post')
]
