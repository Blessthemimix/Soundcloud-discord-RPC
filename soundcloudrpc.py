import time
import logging
from pydbus import SessionBus
from pypresence import Presence

# ---------------- НАСТРОЙКИ ----------------
CLIENT_ID = 'YOUR APPLICATION ID' 
CHECK_INTERVAL = 3
# -------------------------------------------

# Настраиваем логирование, чтобы видеть ошибки, если что-то пойдет не так
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_media_info(bus):
    """
    Сканирует D-Bus на наличие медиаплееров (браузеров) и ищет SoundCloud.
    """
    try:
        # Получаем объект DBus
        remote_object = bus.get("org.freedesktop.DBus", "/org/freedesktop/DBus")
        
        # Список всех активных сервисов
        names = remote_object.ListNames()
        
        # Фильтруем только медиаплееры (org.mpris.MediaPlayer2.*)
        players = [name for name in names if "org.mpris.MediaPlayer2" in name]

        for player_name in players:
            try:
                # Подключаемся к конкретному плееру
                player = bus.get(player_name, "/org/mpris/MediaPlayer2")
                
                # Получаем метаданные
                metadata = player.Metadata
                playback_status = player.PlaybackStatus # "Playing", "Paused", "Stopped"

                # Пропускаем, если ничего не играет
                if playback_status != "Playing":
                    continue
                
                # MPRIS возвращает словарь. Ключи обычно 'xesam:artist', 'xesam:title' и т.д.
                # Данные могут быть None, поэтому используем .get()
                
                # !!! ВАЖНО: Браузеры по-разному отдают название сервиса.
                # Часто SoundCloud пишет свое имя в title или мы можем понять это по url
                
                artist = metadata.get('xesam:artist', ['Unknown'])[0] if isinstance(metadata.get('xesam:artist'), list) else metadata.get('xesam:artist', 'Unknown')
                title = metadata.get('xesam:title', 'Unknown')
                length_micro = metadata.get('mpris:length', 0) # Длина в микросекундах
                
                # Проверка: действительно ли это SoundCloud
                # Обычно браузеры не пишут "SoundCloud" в поле source явно,
                # поэтому нужно отфильтровать по заголовку или логике.
                
                return {
                    "artist": artist,
                    "title": title,
                    "length": length_micro, # Время в микросекундах
                    "status": playback_status
                }
                
            except Exception as e:
                # Некоторые плееры могут исчезнуть или выдать ошибку
                continue
                
    except Exception as e:
        logging.error(f"Ошибка D-Bus: {e}")
    
    return None

def main():
    print("Запуск Arch SoundCloud RPC...")
    
    bus = SessionBus()
    
    try:
        RPC = Presence(CLIENT_ID)
        RPC.connect()
        print("Подключено к Discord!")
    except Exception as e:
        print(f"Ошибка подключения к Discord: {e}")
        return

    last_track_name = None
    start_time = None

    while True:
        info = get_media_info(bus)

        if info:
            current_track_name = f"{info['artist']} - {info['title']}"

            # Если трек сменился
            if current_track_name != last_track_name:
                print(f"Играет: {current_track_name}")
                last_track_name = current_track_name
                start_time = time.time()
            
            # Конвертация микросекунд в секунды для конца трека (опционально)
            # end_time = start_time + (info['length'] / 1_000_000) if info['length'] else None
            
            try:
                RPC.update(
                    state=f"by {info['artist']}",
                    details=info['title'],
                    large_image="logo",  # Убедись, что загрузил картинку 'logo' в Discord Dev Portal
                    large_text="SoundCloud (Arch Linux)",
                    small_image="logo",
                    start=start_time # Показывает "прошло 00:00"
                    # Если захотите, чтобы показывало "осталось 03:20", используйте 'end=end_time' вместо 'start'
                )
            except Exception as e:
                logging.error(f"RPC Update Error: {e}")
        else:
            if last_track_name:
                print("Музыка на паузе или не найдена. Очистка.")
                RPC.clear()
                last_track_name = None

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
