from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView, TemplateView,FormView
from django.db.models import Q
from django.utils import timezone
from blog.forms import ContactForm
from .models import Post, Category, Tag,ContactMessage
from django.contrib import messages
from django.urls import reverse_lazy
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect
from .management.commands.generate_post import Command
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.views import View
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
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
    
    @method_decorator(cache_page(60 * 15))  # Cache for 15 minutes
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_queryset(self):
        return Post.objects.filter(is_published=True).prefetch_related('images')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = context['post']
        
        # Increment view count
        post.view_count += 1
        post.save(update_fields=['view_count'])
        
        # Get related posts with cache
        cache_key = f'related_posts_{post.id}'
        related_posts = cache.get(cache_key)
        
        if not related_posts:
            related_posts = Post.objects.filter(
                is_published=True,
                category=post.category
            ).exclude(id=post.id).order_by('-published_at')[:5]
            cache.set(cache_key, related_posts, 60 * 60)  # Cache for 1 hour
        
        context.update({
            'related_posts': related_posts,
            'meta_description': post.summary,
            'meta_image': post.featured_image_url,
        })
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


class GalleryView(ListView):
    template_name = "blog/gallery.html"
    context_object_name = 'posts'
    paginate_by = 12  
    
    def get_queryset(self):
        return Post.objects.filter(
            is_published=True
        ).prefetch_related('images').order_by('-published_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
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




class ContactView(FormView):
    template_name = 'blog/contact.html'
    form_class = ContactForm  # Specify the form class
    success_url = reverse_lazy('blog:contact')
    
    def form_valid(self, form):
        # Save the contact message to database
        ContactMessage.objects.create(
            name=form.cleaned_data['name'],
            email=form.cleaned_data['email'],
            subject=form.cleaned_data['subject'],
            message=form.cleaned_data['message']
        )
        
        messages.success(self.request, 'Thank you for your message! We will get back to you soon.')
        return super().form_valid(form)
    



@method_decorator(staff_member_required, name='dispatch')
class GeneratePostView(View):
    """
    Admin-only view for manually generating blog posts
    """
    template_name = 'admin/generate_post.html'
    
    def get(self, request, *args, **kwargs):
        """Handle GET requests - show the generation form"""
        return render(request, self.template_name)
    
    def post(self, request, *args, **kwargs):
        """Handle POST requests - process the generation"""
        try:
            cmd = Command()
            category = request.POST.get('category')
            
            # Call the management command with form data
            cmd.handle(category=category or None)
            
            messages.success(request, '🌿 Post generated successfully!')
        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')
            # For debugging in admin (remove in production)
            messages.info(request, f'Debug: {repr(e)}')
        
        return redirect('blog:home')