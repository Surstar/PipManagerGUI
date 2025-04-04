import multiprocessing
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import subprocess
import threading
import sys
import re
import os
import shutil
from packaging import version
from configparser import ConfigParser
multiprocessing.freeze_support()



# 配置信息
PIP_CONFIGS = {
    'default': {'url': 'https://pypi.org/simple', 'trusted_host': 'pypi.org'},
    'tsinghua': {'url': 'https://pypi.tuna.tsinghua.edu.cn/simple', 'trusted_host': 'pypi.tuna.tsinghua.edu.cn'},
    'aliyun': {'url': 'https://mirrors.aliyun.com/pypi/simple/', 'trusted_host': 'mirrors.aliyun.com'},
    'douban': {'url': 'https://pypi.douban.com/simple/', 'trusted_host': 'pypi.douban.com'},
    'ustc': {'url': 'https://pypi.mirrors.ustc.edu.cn/simple/', 'trusted_host': 'pypi.mirrors.ustc.edu.cn'},
    'tencent': {'url': 'https://mirrors.cloud.tencent.com/pypi/simple', 'trusted_host': 'mirrors.cloud.tencent.com'}
}

#添加中文映射
DISPLAY_NAMES = {
    'default': '默认官方源',
    'tsinghua': '清华大学',
    'aliyun': '阿里云',
    'douban': '豆瓣',
    'ustc': '中科大',
    'tencent': '腾讯云',
    'custom': '自定义源'
}


# 新增Tooltip类
class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25

        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        label = ttk.Label(tw, text=self.text, background="#ffffe0",
                          relief="solid", borderwidth=1, padding=(5, 2))
        label.pack()

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
        self.tip_window = None


class SourceSwitcher(tk.Toplevel):
    def __init__(self,parent):
        super().__init__(parent)
        self.title("PIP源切换")
        self.geometry("500x400")
        self.config_path = self.get_config_path()
        self.parent = parent
        self.grab_set()
        self.transient(parent)

        # 界面组件初始化
        self.create_widgets()
        self.update_current_source()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        """关闭窗口时的处理"""
        self.parent.focus_set()  # 将焦点返回父窗口
        self.destroy()

    def get_config_path(self):
        """获取配置文件路径"""
        if os.name == 'nt':
            return os.path.join(os.getenv('APPDATA'), 'pip', 'pip.ini')
        return os.path.expanduser('~/.pip/pip.conf')

    def backup_config(self):
        """创建配置备份"""
        if os.path.exists(self.config_path):
            backup_path = f"{self.config_path}.bak"
            shutil.copyfile(self.config_path, backup_path)
            return backup_path
        return None

    def get_current_source(self):
        """获取当前源配置"""
        if not os.path.exists(self.config_path):
            return 'default'

        config = ConfigParser()
        config.read(self.config_path)

        try:
            url = config.get('global', 'index-url')
            for name, info in PIP_CONFIGS.items():
                if info['url'] == url:
                    return name
            return 'custom'
        except:
            return 'default'

    def update_current_source(self):
        """更新当前源显示"""
        current = DISPLAY_NAMES[self.get_current_source()]
        self.current_var.set(f"当前源: {current}")
        self.status_var.set("就绪")

    def set_source(self):
        """设置源"""
        selected = self.source_var.get()
        custom_url = self.custom_url.get() if selected == 'custom' else None

        try:
            backup_path = self.backup_config()

            # 创建配置目录
            config_dir = os.path.dirname(self.config_path)
            os.makedirs(config_dir, exist_ok=True)

            # 获取配置信息
            if selected == 'custom':
                if not custom_url:
                    messagebox.showerror("错误", "必须提供自定义源URL")
                    return
                config = {'url': custom_url, 'trusted_host': ''}
            else:
                config = PIP_CONFIGS.get(selected)
                if not config:
                    raise ValueError("无效的镜像源")

            # 写入配置文件
            cfg = ConfigParser()
            if os.path.exists(self.config_path):
                cfg.read(self.config_path)

            if not cfg.has_section('global'):
                cfg.add_section('global')

            cfg.set('global', 'index-url', config['url'])
            if config['trusted_host']:
                cfg.set('global', 'trusted-host', config['trusted_host'])
            elif cfg.has_option('global', 'trusted-host'):
                cfg.remove_option('global', 'trusted-host')

            with open(self.config_path, 'w') as f:
                cfg.write(f)

            self.status_var.set(f"成功切换到 {selected.upper()}")
            if backup_path:
                self.status_var.set(self.status_var.get() + f"\n备份文件: {backup_path}")
            self.update_current_source()

        except Exception as e:
            messagebox.showerror("错误", str(e))
            self.status_var.set("操作失败")

    def restore_default(self):
        """恢复默认源"""
        try:
            if os.path.exists(self.config_path):
                backup_path = self.backup_config()
                os.remove(self.config_path)
                self.status_var.set(f"已恢复默认源\n备份文件: {backup_path}")
            else:
                self.status_var.set("已经是默认配置")
            self.update_current_source()
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def create_widgets(self):
        """创建界面组件"""
        # 当前源显示
        self.current_var = tk.StringVar()
        current_label = ttk.Label(
            self,
            textvariable=self.current_var,
            font=('Arial', 12, 'bold'),
            foreground='#2c3e50'
        )
        current_label.pack(pady=10)

        # 源选择框架
        source_frame = ttk.LabelFrame(self, text="选择镜像源")
        source_frame.pack(pady=10, fill='x', padx=20)

        # 预设源选择
        self.source_var = tk.StringVar(value='aliyun')
        sources = list(PIP_CONFIGS.keys())[1:] + ['custom']

        for i, source in enumerate(sources):
            display_name = DISPLAY_NAMES[source]
            url = PIP_CONFIGS.get(source, {}).get('url', '自定义源地址')

            rb = ttk.Radiobutton(
                source_frame,
                text=display_name,  # 仅显示源名称
                variable=self.source_var,
                value=source,
                command=self.toggle_custom_input
            )
            rb.grid(row=i // 2, column=i % 2, sticky='w', padx=10, pady=5)

            # 为每个选项添加Tooltip
            Tooltip(rb, url)  # 绑定悬停提示

        # 自定义源输入
        self.custom_frame = ttk.Frame(source_frame)
        self.custom_label = ttk.Label(self.custom_frame, text="自定义URL:")
        self.custom_url = ttk.Entry(self.custom_frame, width=40)
        self.custom_label.pack(side='left', padx=5)
        self.custom_url.pack(side='left', fill='x', expand=True)

        # 操作按钮
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=15)

        ttk.Button(
            btn_frame,
            text="应用设置",
            command=self.set_source,
            style='Accent.TButton'
        ).pack(side='left', padx=5)

        ttk.Button(
            btn_frame,
            text="恢复默认",
            command=self.restore_default
        ).pack(side='left', padx=5)

        # 状态栏
        self.status_var = tk.StringVar()
        status_bar = ttk.Label(
            self,
            textvariable=self.status_var,
            relief='sunken',
            anchor='w'
        )
        status_bar.pack(side='bottom', fill='x')

        # 样式配置
        self.style = ttk.Style()
        self.style.configure('Accent.TButton', foreground='#3498db', background='#3498db')
        self.style.map('Accent.TButton',
                       background=[('active', '#2980b9')])

    def toggle_custom_input(self):
        """切换自定义源输入框"""
        if self.source_var.get() == 'custom':
            self.custom_frame.grid(row=3, column=0, columnspan=2, pady=5, sticky='ew')
        else:
            self.custom_frame.grid_remove()



class PipInstallerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("pip 图形化管理工具 v1.0")
        self.geometry("800x600")
        self.create_main_widgets()
        self.installed_packages = []  # 新增包列表存储
        self._after_id = None  # 用于延迟搜索

        # 进度条初始化
        self.progress = ttk.Progressbar(
            self,
            mode='indeterminate',
            length=200,
            style='Custom.Horizontal.TProgressbar'
        )
        self.progress.place(relx=0.5, rely=0.95, anchor=tk.CENTER, relwidth=0.8)  # 调整位置
        self.progress.pack_forget()

        # 安装状态跟踪
        self.installing = False
        self.current_process = None
        self.selected_packages = []

        # 创建界面组件
        self.create_widgets()
        self.load_installed_packages()
        self.create_source_button()

    def create_source_button(self):
        # 在工具栏添加按钮
        toolbar = ttk.Frame(self)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        source_btn = ttk.Button(
            toolbar,
            text="切换镜像源",
            command=self.open_source_switcher,
            style='Accent.TButton'
        )
        source_btn.pack(side=tk.LEFT, padx=5, pady=2)

    def open_source_switcher(self):
        """打开镜像源切换窗口"""
        if not hasattr(self, 'source_window') or not self.source_window.winfo_exists():
            self.source_window = SourceSwitcher(self)
            # 绑定关闭事件
            self.source_window.bind("<Destroy>", self.on_source_window_closed)
        else:
            self.source_window.lift()  # 如果窗口已存在则提到最前

    def on_source_window_closed(self, event):
        """镜像源窗口关闭后的处理"""
        # 可以在这里添加源切换后的处理逻辑
        print("镜像源设置窗口已关闭")

    def create_widgets(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 包安装模块
        install_frame = ttk.LabelFrame(main_frame, text="包安装管理")
        install_frame.pack(fill=tk.X, pady=5)

        # 包名称和版本输入
        input_frame = ttk.Frame(install_frame)
        input_frame.pack(fill=tk.X, pady=5)

        ttk.Label(input_frame, text="包名称：").pack(side=tk.LEFT, padx=5)
        self.pkg_entry = ttk.Entry(input_frame, width=25)
        self.pkg_entry.pack(side=tk.LEFT, padx=5)

        ttk.Label(input_frame, text="版本：").pack(side=tk.LEFT, padx=5)
        self.version_entry = ttk.Entry(input_frame, width=15)
        self.version_entry.pack(side=tk.LEFT, padx=5)

        # 安装选项
        options_frame = ttk.Frame(install_frame)
        options_frame.pack(fill=tk.X, pady=5)

        self.user_var = tk.BooleanVar()
        self.upgrade_var = tk.BooleanVar()
        ttk.Checkbutton(options_frame, text="用户模式(--user)", variable=self.user_var).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(options_frame, text="强制升级(--upgrade)", variable=self.upgrade_var).pack(side=tk.LEFT, padx=5)

        # 操作按钮
        btn_frame = ttk.Frame(install_frame)
        btn_frame.pack(fill=tk.X, pady=5)

        self.install_btn = ttk.Button(
            btn_frame,
            text="安装",
            command=self.start_install_thread,
            style='Accent.TButton'
        )
        self.install_btn.pack(side=tk.LEFT, padx=5)


        # 已安装包列表
        list_frame = ttk.LabelFrame(main_frame, text="已安装包列表")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # 列表控件
        self.tree = ttk.Treeview(list_frame, columns=('name', 'version'), show='headings')
        self.tree.heading('name', text='包名称', anchor=tk.W)
        self.tree.heading('version', text='版本', anchor=tk.W)
        self.tree.column('name', width=300)
        self.tree.column('version', width=150)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # 列表操作按钮
        list_btn_frame = ttk.Frame(list_frame)
        list_btn_frame.pack(side=tk.RIGHT, padx=5)

        self.refresh_btn = ttk.Button(
            list_btn_frame,
            text="刷新列表",
            command=self.load_installed_packages
        )
        self.refresh_btn.pack(pady=5)

        self.uninstall_btn = ttk.Button(
            list_btn_frame,
            text="卸载选中",
            command=self.start_uninstall_thread,
            style='Danger.TButton'
        )
        self.uninstall_btn.pack(pady=5)

        # 绑定选择事件
        self.tree.bind('<<TreeviewSelect>>', self.on_package_select)
        self.pkg_entry.bind('<KeyRelease>', self.on_pkg_entry_change)

        # 输出显示区域
        self.output_area = scrolledtext.ScrolledText(
            main_frame,
            wrap=tk.WORD,
            state='disabled',
            height=15
        )
        self.output_area.pack(fill=tk.BOTH, expand=True, pady=5)

        # 状态栏
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(
            self,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # 样式配置
        self.style = ttk.Style()
        self.style.configure('Accent.TButton', foreground='black', background='#28a745')
        self.style.configure('Danger.TButton', foreground='black', background='#dc3545')
        self.style.map('Accent.TButton', background=[('active', '#218838')])
        self.style.map('Danger.TButton', background=[('active', '#c82333')])
        # 进度条样式配置
        self.style.configure('Custom.Horizontal.TProgressbar',
                             thickness=20,
                             troughcolor='#e9ecef',
                             darkcolor='#007bff',
                             lightcolor='#007bff')

    def create_main_widgets(self):
        # 工具栏
        toolbar = ttk.Frame(self)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        # 添加切换源按钮
        source_btn = ttk.Button(
            toolbar,
            text="切换镜像源",
            command=self.open_source_switcher,
            style='Accent.TButton'
        )
        source_btn.pack(side=tk.LEFT, padx=5, pady=2)
    def on_package_select(self, event):
        """处理包选择事件"""
        self.selected_packages = []
        for item in self.tree.selection():
            values = self.tree.item(item, 'values')
            if values:
                self.selected_packages.append(values[0])

    def build_install_command(self, pkg_name):
        """构建安装命令"""
        cmd = [sys.executable, "-m", "pip", "install"]

        # 添加版本
        if self.version_entry.get().strip():
            pkg_name += "==" + self.version_entry.get().strip()

        # 添加选项
        if self.user_var.get():
            cmd.append("--user")
        if self.upgrade_var.get():
            cmd.append("--upgrade")

        cmd.append(pkg_name)
        return cmd

    def start_install_thread(self):
        """启动安装线程"""
        if self.installing:
            messagebox.showwarning("警告", "当前正在执行安装操作，请稍候！")
            return
        self.progress.pack(before=self.status_bar, fill=tk.X, padx=10, pady=5)
        self.progress.start(10)

        pkg_name = self.pkg_entry.get().strip()
        if not pkg_name:
            messagebox.showwarning("输入错误", "请输入要安装的包名称！")
            return

        self.installing = True
        self.install_btn.config(state=tk.DISABLED)
        self.status_var.set("正在安装 {}...".format(pkg_name))
        self.append_output(f"开始安装 {pkg_name}\n")

        install_thread = threading.Thread(
            target=self.install_package,
            args=(pkg_name,),
            daemon=True
        )
        install_thread.start()

    def install_package(self, pkg_name):
        """执行安装操作"""
        try:
            # 检查pip可用性
            if not self.check_pip_available():
                self.show_error("未找到有效的pip环境", critical=True)
                return

            # 执行安装命令
            cmd = [sys.executable, "-m", "pip", "install", pkg_name]
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            self.current_process = process
            # 在安装/卸载时显示进度条
            self.progress = ttk.Progressbar(self, mode='indeterminate')
            self.progress.start()

            # 实时读取输出
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    self.append_output(output)

            # 处理结果
            return_code = process.poll()
            if return_code == 0:
                self.append_output("\n安装成功！\n")
                self.status_var.set(f"{pkg_name} 安装成功")
            else:
                error_msg = self.parse_error(process.stdout.read())
                self.show_error(f"安装失败: {error_msg}")

        except Exception as e:
            self.show_error(f"发生意外错误: {str(e)}")
        finally:
            self.installing = False
            self.current_process = None
            self.after(0, self.install_btn.config, {'state': tk.NORMAL})
            self.after(0, self.progress.pack_forget)
            self.installing = False
            self.after(0, self.progress.stop)


    def check_pip_available(self):
        """验证pip是否可用"""
        try:
            subprocess.check_output(
                [sys.executable, "-m", "pip", "--version"],
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            return True
        except subprocess.CalledProcessError:
            return False
        except Exception:
            return False

    def parse_error(self, output):
        """解析常见错误信息"""
        patterns = {
            "not_found": r"ERROR: Could not find a version that satisfies the requirement (\w+)",
            "network": r"ERROR: Could not install packages due to an OSError",
            "permission": r"ERROR: Could not install packages due to an EnvironmentError: \[Errno 13\]",
            "dependency": r"ERROR: Cannot uninstall '.*'"
        }

        for error_type, pattern in patterns.items():
            if re.search(pattern, output, re.IGNORECASE):
                return {
                    "not_found": "包不存在或名称错误",
                    "network": "网络连接失败，请检查镜像源",
                    "permission": "权限不足，请尝试管理员权限运行",
                    "dependency": "依赖冲突，请使用--user参数"
                }[error_type]
        return "未知错误"

    def append_output(self, text):
        """追加输出信息"""
        self.output_area.config(state=tk.NORMAL)
        self.output_area.insert(tk.END, text)
        self.output_area.see(tk.END)
        self.output_area.config(state=tk.DISABLED)

    def show_error(self, message, critical=False):
        """显示错误信息"""
        self.append_output(f"\n错误: {message}\n")
        self.status_var.set(f"错误: {message}")
        if critical:
            messagebox.showerror("严重错误", message)
        else:
            messagebox.showwarning("操作失败", message)

    def on_closing(self):
        """关闭窗口时的处理"""
        if self.installing and self.current_process:
            self.current_process.terminate()
            self.after(0, self.progress.stop)
            self.after(0, self.progress.pack_forget)
        self.destroy()

    def load_installed_packages(self):
        """加载已安装包列表"""

        def _load():
            try:
                self.status_var.set("正在获取已安装包列表...")
                output = subprocess.check_output(
                    [sys.executable, "-m", "pip", "list", "--format=freeze"],
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                )
                packages = []
                for line in output.split('\n'):
                    if '==' in line:
                        name, ver = line.split('==', 1)
                        packages.append((name.strip(), ver.strip()))

                self.tree.delete(*self.tree.get_children())
                for name, ver in sorted(packages, key=lambda x: x[0].lower()):
                    self.tree.insert('', tk.END, values=(name, ver))

                self.status_var.set(f"已加载 {len(packages)} 个安装包")
                self.installed_packages = packages
                self.update_package_list(packages)
            except Exception as e:
                self.show_error(f"获取已安装列表失败: {str(e)}", critical=False)

        threading.Thread(target=_load, daemon=True).start()

    def update_package_list(self, packages):
        """更新Treeview显示"""
        self.tree.delete(*self.tree.get_children())
        for name, ver in sorted(packages, key=lambda x: x[0].lower()):
            self.tree.insert('', tk.END, values=(name, ver))
        self.status_var.set(f"显示 {len(packages)} 个匹配包")

    def filter_packages(self):
        """执行实际的包过滤"""
        query = self.pkg_entry.get().strip().lower()
        if not query:
            self.update_package_list(self.installed_packages)
            return

        filtered = [
            (name, ver) for name, ver in self.installed_packages
            if query in name.lower()
        ]
        self.update_package_list(filtered)

    def on_pkg_entry_change(self, event):
        """输入内容变化时的处理"""
        # 取消之前的延迟任务
        if self._after_id:
            self.after_cancel(self._after_id)

        # 设置新的延迟任务（300毫秒后执行）
        self._after_id = self.after(300, self.filter_packages)
    def start_uninstall_thread(self):
        """启动卸载线程"""
        self.progress.pack(before=self.status_bar, fill=tk.X, padx=10, pady=5)
        self.progress.start(10)
        if not self.selected_packages:
            messagebox.showwarning("警告", "请先选择要卸载的包！")
            return

        if self.installing:
            messagebox.showwarning("警告", "当前正在执行其他操作，请稍候！")
            return

        confirm = messagebox.askyesno("确认卸载",
                                      f"确定要卸载以下 {len(self.selected_packages)} 个包吗？\n" +
                                      "\n".join(self.selected_packages))
        if not confirm:
            return

        self.installing = True
        self.uninstall_btn.config(state=tk.DISABLED)
        self.status_var.set(f"正在卸载 {len(self.selected_packages)} 个包...")
        self.append_output(f"开始卸载操作\n")

        uninstall_thread = threading.Thread(
            target=self.uninstall_packages,
            daemon=True
        )
        uninstall_thread.start()

    def uninstall_packages(self):
        """执行卸载操作"""
        try:
            for pkg in self.selected_packages:
                cmd = [sys.executable, "-m", "pip", "uninstall", "-y", pkg]
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                )
                self.current_process = process
                # 在安装/卸载时显示进度条
                self.progress = ttk.Progressbar(self, mode='indeterminate')
                self.progress.start()
                while True:
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
                    if output:
                        self.append_output(output)

                return_code = process.poll()
                if return_code != 0:
                    raise Exception(f"卸载 {pkg} 失败")

            self.append_output("\n卸载完成！\n")
            self.status_var.set("卸载操作完成")
            self.load_installed_packages()  # 刷新列表

        except Exception as e:
            self.show_error(f"卸载过程中发生错误: {str(e)}")
        finally:
            self.installing = False
            self.after(0, self.uninstall_btn.config, {'state': tk.NORMAL})
            self.after(0, self.progress.pack_forget)
            self.installing = False
            self.after(0, self.progress.stop)


if __name__ == "__main__":

    multiprocessing.freeze_support()
    app = PipInstallerGUI()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()