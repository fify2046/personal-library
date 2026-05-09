import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import os
import threading
import logging
import glob
import json
from typing import List, Tuple
from db import get_db_manager, get_paths_config, get_db_config, reset_db_manager
from image_processor import ImageProcessor
from pdf_extractor import PDFExtractor
from epub_extractor import EPUBExtractor
import fitz

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EbookExtractorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("个人电子书内容提取工具")
        self.root.geometry("900x700")

        self.db_manager = None
        self.image_processor = None
        self.pdf_extractor = None
        self.epub_extractor = None

        self.book_dir = ""
        self.image_dir = ""
        self.temp_dir = ""

        self.scan_results = []
        self.is_scanning = False
        self.is_extracting = False

        self.success_count = 0
        self.fail_count = 0
        self.skip_count = 0

        self.include_subdirs = tk.BooleanVar(value=True)
        
        # 线程数配置
        self.chapter_workers = tk.IntVar(value=8)
        self.image_workers = tk.IntVar(value=4)
        
        # 配置文件路径
        self.config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")
        self.settings = self._load_settings()
        
        self.disable_index_var = tk.BooleanVar(value=self.settings.get('disable_index', True))
        
        self._init_dirs()
        self._init_ui()
        self._init_extractors()
        self._load_db_config()

    def _load_db_config(self):
        try:
            db_config = get_db_config()
            paths_config = get_paths_config()
            if db_config:
                self.db_host_entry.delete(0, tk.END)
                self.db_host_entry.insert(0, db_config.get('host', 'localhost'))
                self.db_port_entry.delete(0, tk.END)
                self.db_port_entry.insert(0, str(db_config.get('port', 5432)))
                self.db_name_entry.delete(0, tk.END)
                self.db_name_entry.insert(0, db_config.get('database', 'ebook_db'))
                self.db_user_entry.delete(0, tk.END)
                self.db_user_entry.insert(0, db_config.get('user', 'postgres'))
                self.db_pass_entry.delete(0, tk.END)
                self.db_pass_entry.insert(0, db_config.get('password', ''))
            if paths_config:
                images_dir = paths_config.get('images_dir', '')
                if images_dir:
                    self.image_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', images_dir)
                    self.image_dir = os.path.normpath(self.image_dir)
                    self.image_dir_entry.delete(0, tk.END)
                    self.image_dir_entry.insert(0, self.image_dir)
                    self.image_processor = ImageProcessor(self.image_dir)
                    self._init_extractors()
        except Exception as e:
            logger.warning(f"加载配置文件失败: {e}")

    def _load_settings(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"加载配置失败: {e}")
        return {'disable_index': True}
    
    def _save_settings(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存配置失败: {e}")

    def _on_disable_index_changed(self):
        self.settings['disable_index'] = self.disable_index_var.get()
        self._save_settings()

    def _init_dirs(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.image_dir = os.path.join(base_dir, "..\images")

        os.makedirs(self.image_dir, exist_ok=True)

    def _init_extractors(self):
        self.image_processor = ImageProcessor(self.image_dir)
        self.pdf_extractor = PDFExtractor(self.image_processor)
        # 传入UI配置的线程数
        self.epub_extractor = EPUBExtractor(
            self.image_processor,
            chapter_workers=self.chapter_workers.get(),
            image_workers=self.image_workers.get()
        )

    def _init_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        title_label = ttk.Label(main_frame, text="个人电子书内容提取工具", font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=10)

        config_frame = ttk.LabelFrame(main_frame, text="配置", padding="5")
        config_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(config_frame, text="数据库:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.db_host_entry = ttk.Entry(config_frame, width=15)
        self.db_host_entry.insert(0, "localhost")
        self.db_host_entry.grid(row=0, column=1, padx=5)

        self.db_port_entry = ttk.Entry(config_frame, width=8)
        self.db_port_entry.insert(0, "5432")
        self.db_port_entry.grid(row=0, column=2, padx=5)

        self.db_name_entry = ttk.Entry(config_frame, width=12)
        self.db_name_entry.insert(0, "ebook_db")
        self.db_name_entry.grid(row=0, column=3, padx=5)

        self.db_user_entry = ttk.Entry(config_frame, width=10)
        self.db_user_entry.insert(0, "ebook")
        self.db_user_entry.grid(row=0, column=4, padx=5)

        self.db_pass_entry = ttk.Entry(config_frame, width=10, show="*")
        self.db_pass_entry.insert(0, "asdfgh")
        self.db_pass_entry.grid(row=0, column=5, padx=5)

        ttk.Button(config_frame, text="测试连接", command=self.test_db_connection).grid(row=0, column=6, padx=5)

        ttk.Label(config_frame, text="图片目录:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.image_dir_entry = ttk.Entry(config_frame, width=50)
        self.image_dir_entry.insert(0, self.image_dir)
        self.image_dir_entry.grid(row=1, column=1, columnspan=4, padx=5, pady=5)
        ttk.Button(config_frame, text="选择", command=self.select_image_dir).grid(row=1, column=5, padx=5)

        dir_frame = ttk.LabelFrame(main_frame, text="书籍目录", padding="5")
        dir_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        self.book_dir_entry = ttk.Entry(dir_frame, width=60)
        self.book_dir_entry.grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(dir_frame, text="选择目录", command=self.select_book_dir).grid(row=0, column=1, padx=5)
        ttk.Button(dir_frame, text="扫描书籍", command=self.scan_books).grid(row=0, column=2, padx=5)

        self.subdir_check = ttk.Checkbutton(dir_frame, text="包含子目录", variable=self.include_subdirs)
        self.subdir_check.grid(row=0, column=3, padx=5)

        type_frame = ttk.Frame(dir_frame)
        type_frame.grid(row=1, column=0, columnspan=3, pady=5)

        ttk.Label(type_frame, text="处理类型:").pack(side=tk.LEFT, padx=5)

        self.pdf_var = tk.BooleanVar(value=False)
        self.pdf_check = ttk.Checkbutton(type_frame, text="PDF", variable=self.pdf_var)
        self.pdf_check.pack(side=tk.LEFT, padx=5)

        self.epub_var = tk.BooleanVar(value=True)
        self.epub_check = ttk.Checkbutton(type_frame, text="EPUB", variable=self.epub_var)
        self.epub_check.pack(side=tk.LEFT, padx=5)

        ttk.Button(type_frame, text="重置数据", command=self.reset_data).pack(side=tk.LEFT, padx=10)
        ttk.Button(type_frame, text="删除重复图书", command=self.delete_duplicate_books).pack(side=tk.LEFT, padx=10)
        ttk.Button(type_frame, text="数据库维护", command=self.maintain_database).pack(side=tk.LEFT, padx=10)
        
        self.disable_index_check = ttk.Checkbutton(type_frame, text="失效全文索引", variable=self.disable_index_var, command=self._on_disable_index_changed)
        self.disable_index_check.pack(side=tk.LEFT, padx=10)
        ttk.Button(type_frame, text="重建全文索引", command=self.rebuild_trgm_index).pack(side=tk.LEFT, padx=10)

        # 线程数配置
        workers_frame = ttk.LabelFrame(dir_frame, text="线程配置", padding="5")
        workers_frame.grid(row=1, column=3, rowspan=2, padx=10, pady=5, sticky=tk.N)

        ttk.Label(workers_frame, text="章节提取:").grid(row=0, column=0, sticky=tk.W, padx=2)
        self.chapter_workers_spin = ttk.Spinbox(workers_frame, from_=1, to=32, width=5, textvariable=self.chapter_workers)
        self.chapter_workers_spin.grid(row=0, column=1, padx=2)

        ttk.Label(workers_frame, text="图片保存:").grid(row=1, column=0, sticky=tk.W, padx=2, pady=2)
        self.image_workers_spin = ttk.Spinbox(workers_frame, from_=1, to=32, width=5, textvariable=self.image_workers)
        self.image_workers_spin.grid(row=1, column=1, padx=2, pady=2)

        status_frame = ttk.Frame(dir_frame)
        status_frame.grid(row=2, column=0, columnspan=3, pady=5)

        self.scan_label = ttk.Label(status_frame, text="待扫描")
        self.scan_label.pack(side=tk.LEFT, padx=10)

        self.success_label = ttk.Label(status_frame, text="成功: 0", foreground="green")
        self.success_label.pack(side=tk.LEFT, padx=10)

        self.fail_label = ttk.Label(status_frame, text="失败: 0", foreground="red")
        self.fail_label.pack(side=tk.LEFT, padx=10)

        self.skip_label = ttk.Label(status_frame, text="跳过: 0", foreground="orange")
        self.skip_label.pack(side=tk.LEFT, padx=10)

        self.progress_bar = ttk.Progressbar(main_frame, mode='determinate')
        self.progress_bar.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        self.start_button = ttk.Button(main_frame, text="开始提取", command=self.start_extraction, state=tk.DISABLED)
        self.start_button.grid(row=4, column=0, columnspan=3, pady=10)

        log_frame = ttk.LabelFrame(main_frame, text="处理日志", padding="5")
        log_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=80)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(5, weight=1)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def log(self, message: str):
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def select_book_dir(self):
        directory = filedialog.askdirectory(title="选择书籍目录")
        if directory:
            self.book_dir = directory
            self.book_dir_entry.delete(0, tk.END)
            self.book_dir_entry.insert(0, directory)

    def select_image_dir(self):
        directory = filedialog.askdirectory(title="选择图片保存目录")
        if directory:
            self.image_dir = directory
            self.image_dir_entry.delete(0, tk.END)
            self.image_dir_entry.insert(0, directory)
            self.image_processor = ImageProcessor(self.image_dir)
            self._init_extractors()

    def test_db_connection(self):
        try:
            host = self.db_host_entry.get()
            port = int(self.db_port_entry.get())
            database = self.db_name_entry.get()
            user = self.db_user_entry.get()
            password = self.db_pass_entry.get()

            self.db_manager = get_db_manager(host, port, database, user, password)

            if self.db_manager.init_pool():
                if self.db_manager.check_connection():
                    messagebox.showinfo("成功", "数据库连接成功!")
                    self.log("数据库连接测试成功")
                else:
                    messagebox.showerror("失败", "无法连接到数据库，请检查配置")
            else:
                messagebox.showerror("失败", "数据库连接池初始化失败")

        except Exception as e:
            messagebox.showerror("错误", f"连接失败: {str(e)}")
            self.log(f"数据库连接错误: {str(e)}")

    def _drop_trgm_index(self):
        try:
            if not self.db_manager:
                return False
            conn = self.db_manager.acquire_connection()
            try:
                cur = conn.cursor()
                cur.execute("DROP INDEX IF EXISTS idx_paragraphs_content_trgm")
                conn.commit()
                cur.close()
                return True
            finally:
                self.db_manager.release_connection(conn)
        except Exception as e:
            self.log(f"删除索引失败: {e}")
            return False

    def rebuild_trgm_index(self):
        if not self.db_manager:
            messagebox.showwarning("警告", "请先测试数据库连接")
            return
        
        result = messagebox.askyesno("确认", "重建全文索引可能需要较长时间，是否继续？")
        if result:
            self.log("正在重建全文索引，请稍候...")
            threading.Thread(target=self._rebuild_trgm_index_thread, daemon=True).start()

    def _rebuild_trgm_index_thread(self):
        try:
            if not self.db_manager:
                self.root.after(0, lambda: messagebox.showerror("错误", "数据库未连接"))
                return
            
            conn = self.db_manager.acquire_connection()
            try:
                cur = conn.cursor()
                
                self.root.after(0, lambda: self.log("正在删除旧索引..."))
                cur.execute("DROP INDEX IF EXISTS idx_paragraphs_content_trgm")
                conn.commit()
                
                self.root.after(0, lambda: self.log("正在创建 paragraphs 索引..."))
                cur.execute("""
                    CREATE INDEX idx_paragraphs_content_trgm 
                    ON paragraphs USING gin (content gin_trgm_ops)
                """)
                conn.commit()
                
                self.root.after(0, lambda: self.log("全文索引重建完成"))
                self.root.after(0, lambda: messagebox.showinfo("成功", "全文索引重建完成"))
            finally:
                self.db_manager.release_connection(conn)
        except Exception as e:
            self.root.after(0, lambda: self.log(f"重建索引失败: {e}"))
            self.root.after(0, lambda: messagebox.showerror("错误", f"重建索引失败: {e}"))

    def scan_books(self):
        if not self.book_dir or not os.path.exists(self.book_dir):
            messagebox.showwarning("警告", "请先选择有效的书籍目录")
            return

        if not self.pdf_var.get() and not self.epub_var.get():
            messagebox.showwarning("警告", "请至少选择一种处理类型")
            return

        self.scan_results = []
        self.is_scanning = True
        self.start_button.config(state=tk.DISABLED)

        thread = threading.Thread(target=self._scan_books_thread, daemon=True)
        thread.start()

    def reset_data(self):
        if not self.db_manager:
            messagebox.showwarning("警告", "请先测试数据库连接")
            return

        reset_type = "全部"
        if self.pdf_var.get() and not self.epub_var.get():
            reset_type = "PDF"
        elif self.epub_var.get() and not self.pdf_var.get():
            reset_type = "EPUB"
        
        type_hint = f"（{reset_type}）" if reset_type != "全部" else ""
        if not messagebox.askyesno("确认", f"确定要重置{type_hint}数据吗？\n这将删除选类型对应的数据库记录、图片文件和阅读历史、收藏等！"):
            return

        try:
            self.log(f"开始重置数据{type_hint}...")

            import shutil
            
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    if reset_type == "全部":
                        if os.path.exists(self.image_dir):
                            for item in os.listdir(self.image_dir):
                                item_path = os.path.join(self.image_dir, item)
                                if os.path.isdir(item_path):
                                    shutil.rmtree(item_path)
                                elif item != '.write_test':
                                    os.remove(item_path)
                        self.log("图片文件夹已清空")
                        
                        cur.execute("TRUNCATE TABLE reading_history, favorites, reading_list, images, paragraphs, chapters, books RESTART IDENTITY CASCADE")
                    elif reset_type == "PDF":
                        book_ids_query = "SELECT book_id FROM books WHERE file_type = 'pdf'"
                        cur.execute(book_ids_query)
                        book_ids_to_delete = [str(row[0]) for row in cur.fetchall()]
                        for book_id in book_ids_to_delete:
                            book_img_dir = os.path.join(self.image_dir, book_id)
                            if os.path.exists(book_img_dir):
                                shutil.rmtree(book_img_dir)
                        self.log("PDF图片文件夹已清空")
                        
                        cur.execute("DELETE FROM reading_history WHERE book_id IN (SELECT book_id FROM books WHERE file_type = 'pdf')")
                        cur.execute("DELETE FROM favorites WHERE book_id IN (SELECT book_id FROM books WHERE file_type = 'pdf')")
                        cur.execute("DELETE FROM reading_list WHERE book_id IN (SELECT book_id FROM books WHERE file_type = 'pdf')")
                        cur.execute("DELETE FROM images WHERE chapter_id IN (SELECT chapter_id FROM chapters WHERE book_id IN (SELECT book_id FROM books WHERE file_type = 'pdf'))")
                        cur.execute("DELETE FROM paragraphs WHERE chapter_id IN (SELECT chapter_id FROM chapters WHERE book_id IN (SELECT book_id FROM books WHERE file_type = 'pdf'))")
                        cur.execute("DELETE FROM chapters WHERE book_id IN (SELECT book_id FROM books WHERE file_type = 'pdf')")
                        cur.execute("DELETE FROM books WHERE file_type = 'pdf'")
                    else:
                        book_ids_query = "SELECT book_id FROM books WHERE file_type = 'epub'"
                        cur.execute(book_ids_query)
                        book_ids_to_delete = [str(row[0]) for row in cur.fetchall()]
                        for book_id in book_ids_to_delete:
                            book_img_dir = os.path.join(self.image_dir, book_id)
                            if os.path.exists(book_img_dir):
                                shutil.rmtree(book_img_dir)
                        self.log("EPUB图片文件夹已清空")
                        
                        cur.execute("DELETE FROM reading_history WHERE book_id IN (SELECT book_id FROM books WHERE file_type = 'epub')")
                        cur.execute("DELETE FROM favorites WHERE book_id IN (SELECT book_id FROM books WHERE file_type = 'epub')")
                        cur.execute("DELETE FROM reading_list WHERE book_id IN (SELECT book_id FROM books WHERE file_type = 'epub')")
                        cur.execute("DELETE FROM images WHERE chapter_id IN (SELECT chapter_id FROM chapters WHERE book_id IN (SELECT book_id FROM books WHERE file_type = 'epub'))")
                        cur.execute("DELETE FROM paragraphs WHERE chapter_id IN (SELECT chapter_id FROM chapters WHERE book_id IN (SELECT book_id FROM books WHERE file_type = 'epub'))")
                        cur.execute("DELETE FROM chapters WHERE book_id IN (SELECT book_id FROM books WHERE file_type = 'epub')")
                        cur.execute("DELETE FROM books WHERE file_type = 'epub'")
                    
                    conn.commit()
                    self.log("数据库表已清空")

            self.success_count = 0
            self.fail_count = 0
            self.skip_count = 0
            self._update_counts()

            messagebox.showinfo("完成", f"数据重置{type_hint}完成！")
            self.log(f"数据重置{type_hint}完成")

        except Exception as e:
            messagebox.showerror("错误", f"重置失败: {str(e)}")
            self.log(f"重置数据失败: {str(e)}")

    def delete_duplicate_books(self):
        if not self.db_manager:
            messagebox.showwarning("警告", "请先测试数据库连接")
            return

        if not messagebox.askyesno("确认", "确定要删除重复图书吗？\n将保留每组重复图书中的第一条记录，删除其余记录。"):
            return

        try:
            self.log("开始查找重复图书...")
            
            import shutil
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT title, array_agg(CAST(book_id AS VARCHAR)) as book_ids, count(*)
                        FROM books
                        GROUP BY title
                        HAVING count(*) > 1
                    """)
                    duplicates = cur.fetchall()
                    
                    if not duplicates:
                        messagebox.showinfo("完成", "没有发现重复图书！")
                        self.log("没有发现重复图书")
                        return
                    
                    total_deleted = 0
                    for title, book_ids, count in duplicates:
                        book_ids_to_keep = book_ids[1:]
                        for book_id in book_ids_to_keep:
                            try:
                                book_img_dir = os.path.join(self.image_dir, str(book_id))
                                if os.path.exists(book_img_dir):
                                    shutil.rmtree(book_img_dir)
                                
                                cur.execute("SELECT chapter_id FROM chapters WHERE book_id = %s", (str(book_id),))
                                chapters = cur.fetchall()
                                
                                for (chapter_id,) in chapters:
                                    cur.execute("DELETE FROM images WHERE chapter_id = %s", (str(chapter_id),))
                                    cur.execute("DELETE FROM paragraphs WHERE chapter_id = %s", (str(chapter_id),))
                                
                                cur.execute("DELETE FROM chapters WHERE book_id = %s", (str(book_id),))
                                
                                try:
                                    cur.execute("DELETE FROM reading_history WHERE book_id = %s", (str(book_id),))
                                except:
                                    pass
                                try:
                                    cur.execute("DELETE FROM favorites WHERE book_id = %s", (str(book_id),))
                                except:
                                    pass
                                try:
                                    cur.execute("DELETE FROM reading_list WHERE book_id = %s", (str(book_id),))
                                except:
                                    pass
                                
                                cur.execute("DELETE FROM books WHERE book_id = %s", (str(book_id),))
                                
                                total_deleted += 1
                                self.log(f"  已删除重复: {title}")
                            except Exception as e:
                                self.log(f"  删除失败 {book_id}: {str(e)}")
                    
                    conn.commit()
                    self.log(f"删除重复图书完成，共删除 {total_deleted} 条记录")
                    messagebox.showinfo("完成", f"删除重复图书完成！\n共删除 {total_deleted} 条记录")

        except Exception as e:
            messagebox.showerror("错误", f"删除重复图书失败: {str(e)}")
            self.log(f"删除重复图书失败: {str(e)}")

    def maintain_database(self):
        if not self.db_manager:
            messagebox.showwarning("警告", "请先测试数据库连接")
            return

        # 创建维护选项对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("数据库维护")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="选择维护操作:", font=('Arial', 12, 'bold')).pack(pady=10)

        # VACUUM 选项
        vacuum_frame = ttk.LabelFrame(dialog, text="VACUUM (清理死元组)", padding="10")
        vacuum_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(vacuum_frame, text="执行 VACUUM",
                   command=lambda: self._run_vacuum(False, dialog)).pack(side=tk.LEFT, padx=5)
        ttk.Button(vacuum_frame, text="执行 VACUUM FULL (更彻底，会锁表)",
                   command=lambda: self._run_vacuum(True, dialog)).pack(side=tk.LEFT, padx=5)

        # REINDEX 选项
        reindex_frame = ttk.LabelFrame(dialog, text="REINDEX (重建索引)", padding="10")
        reindex_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(reindex_frame, text="重建所有索引",
                   command=lambda: self._run_reindex(dialog)).pack(pady=5)

        # 统计信息
        stats_frame = ttk.LabelFrame(dialog, text="统计信息", padding="10")
        stats_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(stats_frame, text="查看表统计",
                   command=lambda: self._show_table_stats(dialog)).pack(pady=5)

        ttk.Button(dialog, text="关闭", command=dialog.destroy).pack(pady=10)

    def _run_vacuum(self, full: bool, dialog):
        """执行 VACUUM"""
        if full:
            if not messagebox.askyesno("确认", "VACUUM FULL 会锁表，期间无法访问数据，确定执行？"):
                return

        self.log(f"开始执行 VACUUM{' FULL' if full else ''}...")
        dialog.destroy()

        def vacuum_thread():
            try:
                success, msg = self.db_manager.vacuum_analyze(full)
                if success:
                    self.root.after(0, lambda: messagebox.showinfo("完成", msg))
                    self.log(f"VACUUM 完成: {msg}")
                else:
                    self.root.after(0, lambda: messagebox.showerror("错误", f"VACUUM 失败: {msg}"))
                    self.log(f"VACUUM 失败: {msg}")
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"VACUUM 失败: {str(e)}"))
                self.log(f"VACUUM 失败: {str(e)}")

        threading.Thread(target=vacuum_thread, daemon=True).start()

    def _run_reindex(self, dialog):
        """执行 REINDEX"""
        if not messagebox.askyesno("确认", "确定要重建所有索引吗？"):
            return

        self.log("开始重建索引...")
        dialog.destroy()

        def reindex_thread():
            try:
                success, msg = self.db_manager.reindex_tables()
                if success:
                    self.root.after(0, lambda: messagebox.showinfo("完成", msg))
                    self.log(f"重建索引完成: {msg}")
                else:
                    self.root.after(0, lambda: messagebox.showerror("错误", f"重建索引失败: {msg}"))
                    self.log(f"重建索引失败: {msg}")
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"重建索引失败: {str(e)}"))
                self.log(f"重建索引失败: {str(e)}")

        threading.Thread(target=reindex_thread, daemon=True).start()

    def _show_table_stats(self, dialog):
        """显示表统计信息"""
        try:
            stats = self.db_manager.get_table_stats()
            if not stats:
                messagebox.showwarning("警告", "无法获取统计信息")
                return

            # 创建统计窗口
            stats_dialog = tk.Toplevel(dialog)
            stats_dialog.title("数据库表统计信息")
            stats_dialog.geometry("700x400")
            stats_dialog.transient(dialog)

            # 创建表格
            columns = ('表名', '活行数', '死行数', '总大小', '表大小', '索引大小', '上次VACUUM', '上次ANALYZE')
            tree = ttk.Treeview(stats_dialog, columns=columns, show='headings')

            for col in columns:
                tree.heading(col, text=col)
                tree.column(col, width=80)

            tree.column('表名', width=100)
            tree.column('总大小', width=80)
            tree.column('上次VACUUM', width=120)
            tree.column('上次ANALYZE', width=120)

            # 添加数据
            for table_name, info in stats.items():
                tree.insert('', 'end', values=(
                    table_name,
                    info.get('live_rows', 0),
                    info.get('dead_rows', 0),
                    info.get('total_size', ''),
                    info.get('table_size', ''),
                    info.get('index_size', ''),
                    str(info.get('last_vacuum') or info.get('last_autovacuum') or '从未')[:19],
                    str(info.get('last_analyze') or info.get('last_autoanalyze') or '从未')[:19]
                ))

            # 添加滚动条
            scrollbar = ttk.Scrollbar(stats_dialog, orient=tk.VERTICAL, command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)

            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)

            ttk.Button(stats_dialog, text="关闭", command=stats_dialog.destroy).pack(pady=5)

            self.log("已显示表统计信息")

        except Exception as e:
            messagebox.showerror("错误", f"获取统计信息失败: {str(e)}")
            self.log(f"获取统计信息失败: {str(e)}")

    def _scan_books_thread(self):
        self.log("开始扫描书籍目录...")
        self.scan_label.config(text="扫描中...")

        pdf_files = []
        epub_files = []

        include_subdirs = self.include_subdirs.get()

        if self.pdf_var.get():
            if include_subdirs:
                pdf_files = glob.glob(os.path.join(self.book_dir, "**", "*.pdf"), recursive=True)
            else:
                pdf_files = glob.glob(os.path.join(self.book_dir, "*.pdf"))

        if self.epub_var.get():
            if include_subdirs:
                epub_files = glob.glob(os.path.join(self.book_dir, "**", "*.epub"), recursive=True)
            else:
                epub_files = glob.glob(os.path.join(self.book_dir, "*.epub"))

        all_files = pdf_files + epub_files
        total = len(all_files)

        self.log(f"找到 {total} 个文件 (PDF: {len(pdf_files)}, EPUB: {len(epub_files)})")

        for idx, file_path in enumerate(all_files):
            file_type = os.path.splitext(file_path)[1][1:].lower()
            file_size = os.path.getsize(file_path)
            file_name = os.path.basename(file_path)

            self.scan_results.append({
                'path': file_path,
                'name': file_name,
                'type': file_type,
                'size': file_size
            })

            self.scan_label.config(text=f"扫描: {idx + 1}/{total}")

        self.is_scanning = False
        self.scan_label.config(text=f"找到 {total} 个文件")

        if total > 0:
            self.root.after(0, lambda: self.start_button.config(state=tk.NORMAL))

        self.log(f"扫描完成，共发现 {total} 个文件")

    def start_extraction(self):
        if not self.scan_results:
            messagebox.showwarning("警告", "没有可提取的书籍，请先扫描")
            return

        if not self.db_manager:
            messagebox.showwarning("警告", "请先测试数据库连接")
            return

        if self.disable_index_var.get():
            self.log("正在失效全文索引...")
            if self._drop_trgm_index():
                self.log("全文索引已失效，导入速度将提升")
            else:
                self.log("全文索引失效失败，继续导入")

        self.is_extracting = True
        self.start_button.config(state=tk.DISABLED)
        self.success_count = 0
        self.fail_count = 0
        self.skip_count = 0
        self._update_counts()

        thread = threading.Thread(target=self._extraction_thread, daemon=True)
        thread.start()

    def _extraction_thread(self):
        total = len(self.scan_results)

        for idx, book_info in enumerate(self.scan_results):
            file_path = book_info['path']
            file_name = book_info['name']
            file_type = book_info['type']
            file_size = book_info['size']

            self.root.after(0, lambda: self._update_progress(idx + 1, total))
            self.log(f"\n处理 [{idx + 1}/{total}]: {file_name}")
            
            title = os.path.splitext(file_name)[0]
            
            if self.db_manager.book_exists_by_title(title):
                self.log(f"  跳过: 同名图书已存在")
                self.skip_count += 1
                self._update_counts()
                continue

            try:
                book_id = self.db_manager.insert_book(
                    title=title,
                    author=None,
                    file_path=file_path,
                    file_type=file_type,
                    file_size=file_size
                )

                if not book_id:
                    self.log(f"  失败: 无法插入书籍记录")
                    self.fail_count += 1
                    self._update_counts()
                    continue

                self.db_manager.update_book_status(book_id, 'processing')

                if file_type == 'pdf':
                    success, message, data = self.pdf_extractor.extract(file_path, book_id, self._make_progress_callback(idx, total))
                else:
                    success, message, data = self.epub_extractor.extract(file_path, book_id, self._make_progress_callback(idx, total))

                if not success:
                    self.log(f"  失败: {message}")
                    self.db_manager.update_book_status(book_id, 'failed')
                    self.fail_count += 1
                    self._update_counts()
                    continue

                cover_path = data.get('cover_path')
                author = data.get('author')
                if cover_path:
                    self.db_manager.update_book_cover(book_id, cover_path, author)
                    self.log(f"  封面: {cover_path}")

                chapters_data = data.get('chapters_data', [])
                if not chapters_data:
                    self.log(f"  警告: 未提取到章节内容")
                    chapters_data = []

                extracted_images = data.get('extracted_images', [])
                self.log(f"  提取到 {len(extracted_images)} 张图片")
                
                images_by_chapter = {}
                src_to_path = {}
                for img in extracted_images:
                    chapter_order = img.get('chapter_order', 1)
                    if chapter_order not in images_by_chapter:
                        images_by_chapter[chapter_order] = []
                    images_by_chapter[chapter_order].append(img)
                    original_src = img.get('original_src', '')
                    path = img.get('path', '')
                    self.log(f"    图片: 章节{chapter_order}, src={original_src[:50] if original_src else 'None'}..., path={path[:50] if path else 'None'}...")
                    if original_src and path:
                        key = f"{chapter_order}_{original_src}"
                        src_to_path[key] = path
                        src_to_path[original_src] = path
                        cleaned_src = original_src.replace('../', '').replace('./', '')
                        key_cleaned = f"{chapter_order}_{cleaned_src}"
                        src_to_path[key_cleaned] = path

                paragraphs_total = 0
                images_total = 0

                chapters_to_insert = []
                for chapter_data in chapters_data:
                    chapters_to_insert.append({
                        'book_id': book_id,
                        'name': chapter_data.name,
                        'order': chapter_data.order,
                        'level': getattr(chapter_data, 'level', 0),
                        'parent_id': getattr(chapter_data, 'parent_id', None),
                        'temp_id': getattr(chapter_data, 'temp_id', None),
                        'href': getattr(chapter_data, 'href', '')
                    })

                chapter_href_to_id = self.db_manager.insert_chapters_with_hierarchy(chapters_to_insert)
                
                chapter_order_to_id = {}
                for chapter_data in chapters_data:
                    href = getattr(chapter_data, 'href', '')
                    if href and href in chapter_href_to_id:
                        chapter_order_to_id[chapter_data.order] = chapter_href_to_id[href]
                
                # 收集整本书的所有段落和图片，一次性批量插入
                all_paragraphs = []
                all_images = []
                
                for chapter_data in chapters_data:
                    chapter_order = chapter_data.order
                    href = getattr(chapter_data, 'href', '')
                    
                    chapter_id = chapter_href_to_id.get(href) or chapter_order_to_id.get(chapter_order)
                    
                    if not chapter_id:
                        continue

                    if hasattr(chapter_data, 'paragraphs'):
                        for para_idx, para_item in enumerate(chapter_data.paragraphs):
                            if isinstance(para_item, dict):
                                para_type = para_item.get('type', 'text')
                                para_text = para_item.get('content', '')
                                is_footnote = para_item.get('is_footnote', False)
                                if para_type == 'table' and isinstance(para_text, dict):
                                    para_text = json.dumps(para_text, ensure_ascii=False)
                                if para_type == 'image':
                                    original_src = para_item.get('content', '')
                                    if original_src:
                                        key = f"{chapter_order}_{original_src}"
                                        processed_path = src_to_path.get(key)
                                        if not processed_path:
                                            processed_path = src_to_path.get(original_src)
                                        if not processed_path:
                                            cleaned_src = original_src.replace('../', '').replace('./', '')
                                            key_cleaned = f"{chapter_order}_{cleaned_src}"
                                            processed_path = src_to_path.get(key_cleaned)
                                        if not processed_path:
                                            cleaned_src = original_src.replace('../', '').replace('./', '').lstrip('/')
                                            key_cleaned2 = f"{chapter_order}_{cleaned_src}"
                                            processed_path = src_to_path.get(key_cleaned2)
                                        if not processed_path:
                                            src_basename = original_src.split('/')[-1].lower()
                                            for k, v in src_to_path.items():
                                                if k.endswith(f"_{src_basename}") or k == src_basename:
                                                    processed_path = v
                                                    break
                                        if processed_path:
                                            all_paragraphs.append((chapter_id, processed_path, para_idx + 1, 'image', False))
                                elif para_text and para_text.strip():
                                    all_paragraphs.append((chapter_id, para_text, para_idx + 1, para_type, is_footnote))
                            elif isinstance(para_item, str) and para_item.strip():
                                all_paragraphs.append((chapter_id, para_item, para_idx + 1, 'text', False))

                    chapter_images = images_by_chapter.get(chapter_order, [])
                    for img_data in chapter_images:
                        all_images.append((
                            chapter_id,
                            img_data.get('path', ''),
                            img_data.get('order', 1),
                            img_data.get('width', 0),
                            img_data.get('height', 0),
                            img_data.get('alt', ''),
                            img_data.get('original_format', '')
                        ))
                
                # 一次性批量插入所有段落和图片
                if all_paragraphs:
                    self.db_manager.insert_paragraphs_batch_with_footnote(all_paragraphs)
                    paragraphs_total = len(all_paragraphs)
                
                if all_images:
                    self.db_manager.insert_images_batch(all_images)
                    images_total = len(all_images)

                self.db_manager.update_book_status(book_id, 'success')
                self.success_count += 1
                self.log(f"  成功: {len(chapters_data)} 章节, {paragraphs_total} 段落, {images_total} 图片")

            except Exception as e:
                self.log(f"  错误: {str(e)}")
                logger.exception("提取过程出错")
                self.fail_count += 1

            self._update_counts()

        self.root.after(0, self._extraction_complete)

    def _make_progress_callback(self, book_idx, total):
        def callback(current, total_pages):
            self.root.after(0, lambda: self.progress_bar.config(
                value=((book_idx + current / total_pages) / total) * 100
            ))
        return callback

    def _update_progress(self, current, total):
        self.progress_bar.config(value=(current / total) * 100)

    def _update_counts(self):
        self.success_label.config(text=f"成功: {self.success_count}")
        self.fail_label.config(text=f"失败: {self.fail_count}")
        self.skip_label.config(text=f"跳过: {self.skip_count}")
        self.root.update_idletasks()

    def _extraction_complete(self):
        self.is_extracting = False
        self.start_button.config(state=tk.NORMAL)
        self.log("\n" + "=" * 50)
        self.log(f"提取完成! 成功: {self.success_count}, 失败: {self.fail_count}, 跳过: {self.skip_count}")
        self.log("=" * 50)
        messagebox.showinfo("完成", f"提取完成!\n成功: {self.success_count}\n失败: {self.fail_count}\n跳过: {self.skip_count}")

    def on_closing(self):
        if self.is_scanning or self.is_extracting:
            if not messagebox.askyesno("确认", "正在处理中，确定要退出吗?"):
                return

        if self.db_manager:
            self.db_manager.close_pool()

        self.root.destroy()


def main():
    root = tk.Tk()
    app = EbookExtractorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
