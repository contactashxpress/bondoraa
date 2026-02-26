from django.shortcuts import render


def home(request):
    """Affiche la page d'accueil."""
    return render(request, 'index.html')
