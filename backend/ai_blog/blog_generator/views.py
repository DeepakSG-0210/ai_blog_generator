from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings
from .models import BlogPost
import json
import os
from pytube import YouTube
import assemblyai as aai
import openai
from dotenv import load_dotenv
import os
# Create your views here.
@login_required
def index(request):
    return render(request, 'index.html')

@csrf_exempt
def generate_blog(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            yt_link = data['link']
            # return JsonResponse({'content': yt_link})
        except(KeyError, json.JSONDecodeError):
            return JsonResponse({'error': 'Invalid data sent'}, status=400)

        title = yt_title(yt_link)

        transcription = get_transcription(yt_link)
        if not transcription:
            return JsonResponse({'error': 'failed to get transcipt'}, status=500)
        
        blog_content = generate_blog_from_transcription(transcription)
        if not blog_content:
            return JsonResponse({'error': 'failed to generate blog content'}, status=500)

        new_blog_article = BlogPost.objects.create(
            user = request.user ,
            youtube_title = title,
            youtube_link = yt_link,
            generated_content = blog_content,
        )

        new_blog_article.save()

        return JsonResponse({'content': blog_content})
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)

def yt_title(link):
    yt = YouTube(link)
    title = yt.title
    return title

def download_audio(link):
    yt = YouTube(link)
    video = yt.streams.filter(only_audio=True).first()
    out_file = video.download(output_path=settings.MEDIA_ROOT)
    base, ext = os.path.splitext(out_file)
    new_file = base + '.mp3'
    os.rename(out_file, new_file)
    return new_file

def get_transcription(link):
    audio_file = download_audio(link)
    load_dotenv()
    aai.settings.api_key = os.getenv('AAI_API_KEY')

    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(audio_file)

    return transcript.text

def generate_blog_from_transcription(transcript):
    load_dotenv()  # take environment variables from .env.
    openai.api_key = os.getenv('OPENAI_API_KEY')
    prompt = f"Based on the following transcript from a YouTube video, write a comprehensive blog article, write it based on the transcipt, but do not make it look like a youtube video, make it look like a proper blog article: \n\n{transcript}\n\nArticle:"
    response = openai.chat.completions.create(
            model="gpt-3.5-turbo-1106",  # Assuming you use an available GPT model
            messages=[{"role": "system", "content": prompt}],
            max_tokens=1500
        )
        
    generated_content = response.choices[0].message.content.strip()
    return generated_content

def blog_list(request):
    blog_articles = BlogPost.objects.filter(user = request.user)
    return render(request, 'all-blogs.html', {'blog_articles': blog_articles})

def blog_details(request, pk):
    blog_article_detail = BlogPost.objects.get(id = pk)
    if request.user == blog_article_detail.user:
        return render(request, 'blog-details.html', {'blog_article_detail': blog_article_detail})
    else:
        return redirect('/')

def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('/')
        else:
            error_message = 'Username or Password mismatch'
            return render(request, 'signup.html', {'error_message':error_message})

    return render(request, 'login.html')

def user_signup(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        repeatPassword = request.POST['repeatPassword']

        if password == repeatPassword:
            try:
                user = User.objects.create_user(username, email, password)
                user.save()
                login(request, user)
                return redirect('/')
            except:
                error_message = 'Error creating account'
                return render(request, 'signup.html', {'error_message':error_message})
        else:
            error_message = 'Password do not match'
            return render(request, 'signup.html', {'error_message':error_message})
    return render(request, 'signup.html')

def user_logout(request):
    logout(request)
    return redirect('/')
