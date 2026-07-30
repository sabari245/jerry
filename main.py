from pathlib import Path

from jerry import Jerry

output_dir = Path("./output")

def main():
    scraper = Jerry()
    manga = scraper.search("release that witch")[0]
    print(f"manga.title: {manga.title}")
    print(f"chapter_count: {manga.chapter_count()}")

    chapter = manga.chapter(1)
    print(f"chapter: {chapter.title}")
    chapter.save(output_dir)
    

if __name__ == "__main__":
    main()
