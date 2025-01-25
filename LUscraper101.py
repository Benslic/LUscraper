import os
import re
import zipfile
from lxml import html
import requests
from urllib.parse import unquote, urlparse
import shutil
from threading import Thread
from getpass import getpass  
import time
import sys
from PIL import Image  # For image processing
import numpy as np




COURSE_LINKS = [
    "https://estudijas.lu.lv/course/view.php?id=18902",
    "https://estudijas.lu.lv/course/view.php?id=16482",
    "https://estudijas.lu.lv/course/view.php?id=13607",
    "https://estudijas.lu.lv/course/view.php?id=13889",
    "https://estudijas.lu.lv/course/view.php?id=18858",
    "https://estudijas.lu.lv/course/view.php?id=13603",
    "https://estudijas.lu.lv/course/view.php?id=11551",
]



# Define MIME types for files
FILE_MIME_TYPES = [
    # Document Formats
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.oasis.opendocument.text",  # .odt
    "application/vnd.oasis.opendocument.spreadsheet",  # .ods
    "application/vnd.oasis.opendocument.presentation",  # .odp
    "text/plain",  # .txt
    "application/rtf",  # .rtf
    "text/csv",  # .csv
    "text/html",  # .html
    "application/xml",  # .xml

    # Image Formats
    "image/png",  # .png
    "image/jpeg",  # .jpg, .jpeg
    "image/gif",  # .gif
    "image/bmp",  # .bmp
    "image/tiff",  # .tiff
    "image/svg+xml",  # .svg

    # Archive Formats
    "application/zip",  # .zip
    "application/x-rar-compressed",  # .rar
    "application/x-tar",  # .tar
    "application/gzip",  # .gz
    "application/x-7z-compressed",  # .7z

    # Audio Formats
    "audio/mpeg",  # .mp3
    "audio/wav",  # .wav
    "audio/ogg",  # .ogg
    "audio/flac",  # .flac

    # Video Formats
    "video/mp4",  # .mp4
    "video/x-msvideo",  # .avi
    "video/x-matroska",  # .mkv
    "video/quicktime",  # .mov
    "video/webm",  # .webm

    # Programming and Data Formats
    "application/json",  # .json
    "application/javascript",  # .js
    "text/x-python",  # .py
    "text/x-java-source",  # .java
    "application/sql",  # .sql

    # Other Formats
    "application/octet-stream",  # .exe, .bin
    "application/x-apple-diskimage",  # .dmg
    "application/x-iso9660-image",  # .iso
]

# Define file extensions for files
FILE_EXTENSIONS = [
    # Document Formats
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".odt", ".ods", ".odp", ".txt", ".rtf", ".csv", ".html", ".xml",

    # Image Formats
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".svg",

    # Archive Formats
    ".zip", ".rar", ".tar", ".gz", ".7z",

    # Audio Formats
    ".mp3", ".wav", ".ogg", ".flac",

    # Video Formats
    ".mp4", ".avi", ".mkv", ".mov", ".webm",

    # Programming and Data Formats
    ".json", ".js", ".py", ".java", ".sql",

    # Other Formats
    ".exe", ".dmg", ".iso",
]



with open(os.devnull, 'w') as f:
    # Redirect stdout to devnull
    old_stdout = sys.stdout
    sys.stdout = f
    try:
        from pygame import mixer
    finally:
        # Restore stdout
        sys.stdout = old_stdout


def get_user_info(session):
    profile_url = "https://estudijas.lu.lv/user/profile.php"
    response = session.get(profile_url)
    tree = html.fromstring(response.text)

    # Find the <div> with class "page-header-image mr-2"
    div_tag = tree.xpath('//div[contains(@class, "page-header-image mr-2")]')
    if not div_tag:
        print("[ERROR] Could not find user profile div!")
        return None, None

    # Find the <img> tag with the structure "user/icon/maker/" inside the div
    img_tag = div_tag[0].xpath('.//img[contains(@src, "user/icon/maker/")]')
    if not img_tag:
        print("[ERROR] Could not find user image tag!")
        return None, None

    img_tag = img_tag[0]
    image_url = img_tag.get("src")
    user_name = img_tag.get("title")

    return user_name, image_url

def download_user_image(session, image_url):
    try:
        response = session.get(image_url)
        response.raise_for_status()

        # Save the image temporarily
        image_path = "user_image.jpg"
        with open(image_path, "wb") as f:
            f.write(response.content)

        return image_path
    except Exception as e:
        print(f"[ERROR] Failed to download user image: {str(e)}")
        return None    

def display_image_in_console(image_path, width=50):
    try:
        # Open the image
        img = Image.open(image_path)

        # Resize the image to fit the console width
        aspect_ratio = img.height / img.width
        height = int(width * aspect_ratio)
        img = img.resize((width, height))

        # Convert the image to grayscale
        img = img.convert("L")

        # Map grayscale values to ASCII characters
        ascii_chars = "@%#*+=-:. "  # Characters ordered by intensity
        pixels = np.array(img)

        # Normalize pixel values to the range of ascii_chars
        pixels = (pixels / 255) * (len(ascii_chars) - 1)
        pixels = pixels.astype(int)

        # Generate ASCII art
        ascii_art = "\n".join(
            "".join(ascii_chars[pixel] for pixel in row) for row in pixels
        )

        # Display the ASCII art
        print(ascii_art)
    except Exception as e:
        print(f"[ERROR] Failed to display image: {str(e)}")
        

def login_to_moodle(session, login_url, username, password):
    """Logs into Moodle using username and password."""
    try:
        # Get login page to extract CSRF token
        response = session.get(login_url)
        tree = html.fromstring(response.text)
        
        # Extract logintoken
        logintoken = tree.xpath('//input[@name="logintoken"]/@value')
        if not logintoken:
            print("[ERROR] Could not find login token!")
            return False
        logintoken = logintoken[0]

        # Prepare login payload
        login_data = {
            "username": username,
            "password": password,
            "logintoken": logintoken
        }

        # Submit login form
        response = session.post(login_url, data=login_data)

        # Verify login success by checking for logout link
        if 'login/logout.php' in response.text:
            print("[INFO] Login successful!")
            return True
        print("[ERROR] Incorrect password. Login failed!")
        return False
        
    except Exception as e:
        print(f"[ERROR] Login failed: {str(e)}")
        return False
    
#def get_course_links():
    #return COURSE_LINKS

def get_course_links():
    print("Enter the course links (one per line). Press Enter twice to finish:")
    course_links = []
    while True:
        link = input(":").strip()
        if link:
            course_links.append(link)
        else:
            break
    return course_links

def download_files_from_course(session, course_url, output_dir):
    """Downloads all files from a course page using the mod/resource links."""
    try:
        response = session.get(course_url)
        tree = html.fromstring(response.text)
        
        # Extract course name (updated XPath)
        course_name = tree.xpath('//*[contains(@class, "page-header-headings")]//text()')
        if not course_name:
            print(f"[ERROR] Could not extract course name from {course_url}")
            return False
        course_name = " ".join(course_name).strip()  # Join all text nodes and strip whitespace
        
        # Create course directory
        course_path = os.path.join(output_dir, sanitize_filename(course_name))
        os.makedirs(course_path, exist_ok=True)
        
        # Find all file links with the structure https://estudijas.lu.lv/mod/resource
        file_links = tree.xpath('//a[contains(@href, "mod/resource")]')
        
        download_count = 0
        for link in file_links:
            file_url = link.get("href")
            file_name = link.xpath('.//span[@class="instancename"]/text()')
            
            if not file_name:
                print(f"[WARNING] Skipping link {file_url}: No filename found")
                continue
            file_name = file_name[0].strip()  # Extract the filename from the span
            
            # Handle relative URLs
            if not file_url.startswith("http"):
                file_url = "https://estudijas.lu.lv" + file_url
                
            try:
                print(f"[downloading] {file_name} from {file_url}")

                response_head = session.get(file_url, stream=True)
                content_type = response_head.headers.get("Content-Type", "").lower()
                
                # Check if the link is a file or a page
                is_file = (
                    any(ct in content_type for ct in FILE_MIME_TYPES)
                    or any(file_url.lower().endswith(ext) for ext in FILE_EXTENSIONS)
                )

                if is_file and "text/html" not in content_type:
                    file_response = session.get(file_url, stream=True)
                    file_response.raise_for_status()
                    
                    # Extract file extension from the URL or Content-Disposition header
                    file_extension = get_file_extension(file_response, file_url)
                    file_name_with_extension = f"{file_name}{file_extension}"
                    
                    file_path = os.path.join(course_path, sanitize_filename(file_name_with_extension))
                    
                    with open(file_path, "wb") as f:
                        for chunk in file_response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    download_count += 1
                    print("[SUCCESS] Downloaded", file_name_with_extension)
                else:
                    print(f"[INFO] {file_name} is not a direct file link.")
                    print(f"[INFO] Attempting to scrape embedded files from {file_url}")
                    # Treat it as a page and scrape for embedded files
                    embedded_files = scrape_php_page(session, file_url)
                    if not embedded_files:
                        print(f"[WARNING] No embedded files found in {file_url}")
                        continue
                    
                    # Download each embedded file
                    for embedded_url in embedded_files:
                        embedded_response = session.get(embedded_url, stream=True)
                        embedded_response.raise_for_status()
                        
                        # Extract the filename from the URL
                        embedded_filename = os.path.basename(urlparse(embedded_url).path)
                        file_path = os.path.join(course_path, sanitize_filename(file_name + "_" + embedded_filename))
                        
                        with open(file_path, "wb") as f:
                            for chunk in embedded_response.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                        print("[SUCCESS] Downloaded", sanitize_filename(file_name + "_" + embedded_filename))
                        download_count += 1
                        
            except Exception as e:
                print(f"[ERROR] Failed to download {file_name}: {str(e)}")
                
        print(f"[INFO] Downloaded {download_count} files for {course_name}")
        if download_count == 0:
            os.rmdir(course_path) 
            return False 
        return True
    except Exception as e:
        print(f"[ERROR] Course processing failed: {str(e)}")
        return False

def scrape_php_page(session, php_url):
    """Scrapes a .php page for embedded files with the structure .../mod_resource/content/."""
    try:
        response = session.get(php_url)
        tree = html.fromstring(response.text)
        
        # Find all embedded files with the structure .../mod_resource/content/
        embedded_files = tree.xpath('//img[contains(@src, "mod_resource/content")]/@src')
        embedded_files += tree.xpath('//a[contains(@href, "mod_resource/content")]/@href')
        
        # Ensure URLs are absolute
        embedded_files = [
            "https://estudijas.lu.lv" + url if not url.startswith("http") else url
            for url in embedded_files
        ]
        
        return embedded_files
    except Exception as e:
        print(f"[ERROR] Failed to scrape {php_url}: {str(e)}")
        return []

def get_file_extension(response, file_url):
    """
    Extracts the file extension from the URL or Content-Disposition header.
    Returns the extension (e.g., ".pdf") or a default extension if not found.
    """
    # Try to get the extension from the Content-Disposition header
    content_disposition = response.headers.get("Content-Disposition", "")
    if content_disposition:
        # Extract filename from Content-Disposition header
        filename_match = re.findall('filename="([^"]+)"', content_disposition)
        if filename_match:
            filename = unquote(filename_match[0])  # Decode URL-encoded filenames
            _, extension = os.path.splitext(filename)
            if extension:
                return extension
    
    # Try to get the extension from the URL
    parsed_url = urlparse(file_url)
    _, extension = os.path.splitext(parsed_url.path)
    if extension:
        return extension
    
    # Fallback to a default extension if no extension is found
    return ".bin"

def sanitize_filename(filename):
    """Cleans invalid characters from filenames."""
    return re.sub(r'[<>:"/\\|?*]', '_', filename).strip()

def create_zip(output_dir, zip_name):
    """Creates a .zip file of the output directory."""
    try:
        # Check if the output directory is empty
        if not os.listdir(output_dir):
            print(f"[ERROR] Cannot create ZIP: Directory '{output_dir}' is empty.")
            return False
        with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(output_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, output_dir)
                    zipf.write(file_path, arcname)
        print(f"[SUCCESS] Created ZIP archive: {zip_name}")
        return True
    except Exception as e:
        print(f"[ERROR] ZIP creation failed: {str(e)}")
        return False

def get_unique_output_dir(base_dir):
    """Returns a unique directory name by appending a number if the base directory already exists."""
    counter = 1
    output_dir = base_dir
    while os.path.exists(output_dir):
        output_dir = f"{base_dir}_{counter}"
        counter += 1
    return output_dir

def get_unique_filename(base_name):
    counter = 1
    file_name, file_extension = os.path.splitext(base_name)  # Split name and extension
    unique_name = base_name

    # Check if the file already exists
    while os.path.exists(unique_name):
        unique_name = f"{file_name}_{counter}{file_extension}"  # Append number before extension
        counter += 1

    return unique_name

def play_music(mp3_file):
    """Plays background music from an MP3 file using pygame."""
    try:
        # Get the path to the bundled file
        if getattr(sys, 'frozen', False):
            # Running as a bundled executable
            base_path = sys._MEIPASS
        else:
            # Running as a normal Python script
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        mp3_path = os.path.join(base_path, mp3_file)

        if not os.path.exists(mp3_path):
            print(f"[ERROR] Music file '{mp3_path}' not found!")
            return

        print(f"[INFO] Playing background music: {mp3_path}")
        mixer.init()
        mixer.music.load(mp3_path)
        mixer.music.play(loops=-1)

        # Wait for the music to start playing
        while not mixer.music.get_busy():
            time.sleep(0.1)
    except Exception as e:
        print(f"[ERROR] Failed to play music: {str(e)}")

def goodbuy(session,user_name,image_url):
    if user_name and image_url:        
        # Download and display the user's image
        image_path = download_user_image(session, image_url)
        if image_path:
            display_image_in_console(image_path)
            os.remove(image_path)  # Clean up the temporary image file 
        print(f"\nPaldies, ka izmantojāt manu programmu, {user_name}. Novēlu jums jauku dienu!")
        

def main():
    # Configuration
    config = {
        "login_url": "https://estudijas.lu.lv/login/index.php",
        "output_dir": "MoodleDownloads",
        "zip_name": "Courses_Data.zip",
        "music_file": "slow.mp3"  # Path to the background music file	
    }
    
    config["zip_name"] = get_unique_filename(config["zip_name"])


    print("\t\tMoodle\\Estudijas Downloader")
    print("\t\t===========================")
    print("This program downloads all files (materials) from the courses provided via links.")
    print("You will be prompted to enter course links, login credentials, and a password,\n\
and the program will securely download and save the files for you.")
    print(f"All downloaded files will be saved to a ZIP archive named '{config["zip_name"]}'.\
This archive will be created in the same directory as the program.")
    print("IMPORTANT: Your data is confidential.\
\n\t- The program does not store, share, or transmit your password or any other personal information.\
\n\t- All downloaded files are saved locally on your computer.\
\n\t- The program does not connect to any external servers except the official Moodle site.")

    print("Here is an example of the link:\nhttps://estudijas.lu.lv/course/view.php?id=11674")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    })

    course_links = get_course_links()
    if not course_links:
        print("[ERROR] No course links provided!")
        return
   
    # Get login credentials from the user
    username = input("Enter your username: ").strip()
    while True:
        password = getpass("Enter your password (or press Enter to exit): ").strip()
        if not password:  # If Enter is pressed without typing a password
            print("[INFO] Login canceled by user. Exiting...")
            return

        # Attempt to log in
        if login_to_moodle(session, config["login_url"], username, password):
            break  # Exit the loop if login is successful
        else:
            print("[INFO] Please try again or press Enter to exit.")
   
    music_thread = Thread(target=play_music, args=(config["music_file"],))
    music_thread.daemon = True  # Ensure the thread stops when the main program exits
    music_thread.start()
    
    config["output_dir"] = get_unique_output_dir(config["output_dir"])
    print(f"[INFO] Using output directory: {config['output_dir']}")

    # Get user info and display farewell message
    user_name, image_url = get_user_info(session)

    # Download files for each course
    for course_url in course_links:
        print(f"\n[INFO] Processing course: {course_url}")
        download_files_from_course(session, course_url, config["output_dir"])

    # Create final ZIP archive
    print("\n[INFO] Creating ZIP archive...")
    if create_zip(config["output_dir"], config["zip_name"]):
        print("\n[SUCCESS] Script completed successfully!")
        try:
            shutil.rmtree(config["output_dir"])
            print(f"[INFO] Deleted (previously created) output directory: {config['output_dir']}")
        except Exception as e:
            print(f"[ERROR] Failed to delete output directory: {str(e)}")
        goodbuy(session,user_name,image_url)
    else:
        print("[WARNING] Script completed with some errors")
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()