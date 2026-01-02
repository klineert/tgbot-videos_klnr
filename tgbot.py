import re
import os
import subprocess
import uuid
import tempfile
import glob
import shutil
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

TOKEN = "8278165645:AAE19UDVruyeutpISRiedlIA6kYGAkR7PXk"

TIKTOK_REGEX = r"(https?://(www\.)?(vm\.tiktok\.com|tiktok\.com)/\S+)"


DEFAULT_FFMPEG_PATH = r"C:\ffmpeg\bin\ffmpeg.exe"
env_ffmpeg = os.environ.get('FFMPEG_PATH')
if env_ffmpeg and os.path.exists(env_ffmpeg):
    FFMPEG_EXE = env_ffmpeg
else:
    which = shutil.which('ffmpeg')
    if which:
        FFMPEG_EXE = which
    elif os.path.exists(DEFAULT_FFMPEG_PATH):
        FFMPEG_EXE = DEFAULT_FFMPEG_PATH
    else:
        FFMPEG_EXE = None

FFMPEG_DIR = os.path.dirname(FFMPEG_EXE) if FFMPEG_EXE else None

async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    match = re.search(TIKTOK_REGEX, update.message.text)
    if not match:
        return  

    url = match.group(0)
    chat_id = update.effective_chat.id

    

    
    temp_dir = tempfile.gettempdir()
    temp_base = os.path.join(temp_dir, f"tiktok_{uuid.uuid4()}")
    downloaded_file = None

    
    try:
        import yt_dlp

        ydl_opts = {
            'outtmpl': temp_base + '.%(ext)s',
            'format': 'mp4/best',
            'merge_output_format': 'mp4',
            'quiet': True,
            'no_warnings': True,
        }
        if FFMPEG_EXE:
            
            ydl_opts['ffmpeg_location'] = FFMPEG_EXE

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        matches = glob.glob(temp_base + '.*')
        if matches:
            downloaded_file = matches[0]
        else:
            raise FileNotFoundError('Файл не найден после скачивания')

        with open(downloaded_file, 'rb') as video:
            await context.bot.send_video(chat_id, video, supports_streaming=True)

    except Exception as e:
        
        print('yt_dlp Python API error:', e)
        try:
            filename = temp_base + '.mp4'
            cli_args = [
                'yt-dlp',
                '-o', filename,
                '--merge-output-format', 'mp4',
                '--user-agent', 'Mozilla/5.0',
                url
            ]
            if FFMPEG_DIR:
                cli_args[3:3] = ['--ffmpeg-location', FFMPEG_DIR]

            result = subprocess.run(
                cli_args,
                capture_output=True,
                text=True,
                check=True
            )

            if os.path.exists(filename):
                with open(filename, 'rb') as video:
                    await context.bot.send_video(chat_id, video, supports_streaming=True)
                downloaded_file = filename
            else:
                print('yt-dlp CLI did not produce a file')
                await context.bot.send_message(chat_id, '❌ Не удалось скачать видео')

        except subprocess.CalledProcessError as e2:
            print('yt-dlp CLI error:', e2.stderr)
            await context.bot.send_message(chat_id, '❌ Не удалось скачать видео')

        except Exception as e2:
            print('Fallback error:', e2)
            await context.bot.send_message(chat_id, '❌ Ошибка бота')

    finally:
        
        for p in glob.glob(temp_base + '.*'):
            try:
                os.remove(p)
            except Exception:
                pass


app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))

print("✅ TikTok bot запущен")
app.run_polling()
