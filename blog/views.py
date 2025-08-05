from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView, TemplateView
from django.db.models import Q
from django.utils import timezone
from .models import Post, Category, Tag

class PostListView(ListView):
    model = Post
    template_name = "blog/index.html"
    context_object_name = "posts"
    ordering = ['-published_at']
    paginate_by = 6
    
    def get_queryset(self):
        queryset = Post.objects.filter(is_published=True).select_related()
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['featured_posts'] = Post.objects.filter(
            is_published=True, 
            is_featured=True
        ).order_by('-published_at')[:3]
        context['categories'] = Category.objects.all()
        return context


class PostDetailView(DetailView):
    model = Post
    template_name = "blog/post_detail.html"
    context_object_name = "post"
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def get_queryset(self):
        return Post.objects.filter(is_published=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = context['post']
        
        # Increment view count
        post.view_count += 1
        post.save(update_fields=['view_count'])
        
        # Get related posts
        related_posts = Post.objects.filter(
            is_published=True,
            category=post.category
        ).exclude(id=post.id).order_by('-published_at')[:3]
        
        context['related_posts'] = related_posts
        context['categories'] = Category.objects.all()
        return context


class CategoryPostListView(ListView):
    model = Post
    template_name = "blog/category_posts.html"
    context_object_name = "posts"
    ordering = ['-published_at']
    paginate_by = 9
    
    def get_queryset(self):
        category_slug = self.kwargs.get('category_slug')
        self.category = get_object_or_404(Category, slug=category_slug)
        return Post.objects.filter(
            is_published=True,
            category=self.category.category
        ).select_related()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        context['categories'] = Category.objects.all()
        return context


class TagPostListView(ListView):
    model = Post
    template_name = "blog/tag_posts.html"
    context_object_name = "posts"
    ordering = ['-published_at']
    paginate_by = 9
    
    def get_queryset(self):
        tag_slug = self.kwargs.get('tag_slug')
        self.tag = get_object_or_404(Tag, slug=tag_slug)
        return Post.objects.filter(
            is_published=True,
            tags=self.tag
        ).select_related()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tag'] = self.tag
        context['categories'] = Category.objects.all()
        return context


class SearchPostListView(ListView):
    model = Post
    template_name = "blog/search_results.html"
    context_object_name = "posts"
    ordering = ['-published_at']
    paginate_by = 9
    
    def get_queryset(self):
        query = self.request.GET.get('q', '')
        if query:
            return Post.objects.filter(
                is_published=True
            ).filter(
                Q(title__icontains=query) |
                Q(content__icontains=query) |
                Q(summary__icontains=query) |
                Q(scientific_name__icontains=query) |
                Q(tags__name__icontains=query)
            ).distinct()
        return Post.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        context['categories'] = Category.objects.all()
        return context


class AboutView(TemplateView):
    template_name = "blog/about.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_posts'] = Post.objects.filter(is_published=True).count()
        context['categories'] = Category.objects.all()
        return context


class GalleryView(TemplateView):
    template_name = "blog/gallery.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['posts'] = Post.objects.filter(
            is_published=True
        ).order_by('-published_at')
        context['categories'] = Category.objects.all()
        return context


class BlogView(ListView):
    model = Post
    template_name = "blog/blog.html"
    context_object_name = "posts"
    ordering = ['-published_at']
    paginate_by = 9
    
    def get_queryset(self):
        queryset = Post.objects.filter(is_published=True).select_related()
        
        # Filter by category if specified
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['selected_category'] = self.request.GET.get('category', '')
        return context


class ContactView(TemplateView):
    template_name = "blog/contact.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        return context
