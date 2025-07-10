# gui/app.py
import tkinter as tk
from tkinter import ttk, messagebox
from core.data_manager import DataManager
from gui.chart_canvas import ChartCanvas

class ScheduleApp(tk.Tk):
    """
    家族在宅スケジュール管理アプリケーションのメインウィンドウクラス。
    UIの構築、データマネージャーとチャートキャンバスの連携を管理する。
    """
    def __init__(self):
        super().__init__()
        self.title("家族在宅スケジュール管理アプリ")
        self.geometry("1600x1200") # 初期ウィンドウサイズ
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # データマネージャーのインスタンス化
        self.data_manager = DataManager()

        # UIのセットアップ
        self._setup_ui()
        
        # 既存のメンバーをリストボックスにロード
        self.load_initial_data_into_listbox()
        
        # ウィンドウが完全に描画された後にガントチャートを更新する
        # これにより、初期サイズが正しく取得され、チャートが適切に描画される
        self.update_idletasks() 
        self.chart_canvas.update_gantt_chart()

    def _setup_ui(self):
        """
        アプリケーションのUI要素を構築する。
        """
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # メンバー管理フレーム
        member_frame = ttk.LabelFrame(main_frame, text="メンバー管理", padding="10")
        member_frame.pack(fill=tk.X, pady=5)

        member_name_label = ttk.Label(member_frame, text="メンバー名:")
        member_name_label.pack(side=tk.LEFT, padx=5)
        self.member_name_entry = ttk.Entry(member_frame, width=20)
        self.member_name_entry.pack(side=tk.LEFT, padx=5)
        add_member_button = ttk.Button(member_frame, text="メンバーを追加", command=self.add_member_gui)
        add_member_button.pack(side=tk.LEFT, padx=5)
        # Enterキーでメンバー追加
        self.member_name_entry.bind("<Return>", lambda event: self.add_member_gui())

        delete_member_button = ttk.Button(member_frame, text="選択メンバーを削除", command=self.delete_member_gui)
        delete_member_button.pack(side=tk.LEFT, padx=5)


        # スケジュール設定フレーム
        schedule_frame = ttk.LabelFrame(main_frame, text="スケジュール設定", padding="10")
        schedule_frame.pack(fill=tk.X, pady=5)

        # メンバーリストボックス (選択用)
        ttk.Label(schedule_frame, text="メンバー選択:").pack(side=tk.LEFT, padx=5)
        self.member_listbox = tk.Listbox(schedule_frame, height=5, selectmode=tk.SINGLE)
        self.member_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        # スクロールバー
        scrollbar = ttk.Scrollbar(schedule_frame, orient="vertical", command=self.member_listbox.yview)
        scrollbar.pack(side=tk.LEFT, fill="y")
        self.member_listbox.config(yscrollcommand=scrollbar.set)


        # 時間入力部
        time_input_frame = ttk.Frame(schedule_frame)
        time_input_frame.pack(side=tk.LEFT, padx=10)

        ttk.Label(time_input_frame, text="開始時間 (0-23):").pack(anchor="w")
        self.start_hour_entry = ttk.Entry(time_input_frame, width=5)
        self.start_hour_entry.pack(anchor="w")
        # Enterキーで終了時刻入力欄にフォーカス移動
        self.start_hour_entry.bind("<Return>", lambda event: self.end_hour_entry.focus_set())


        ttk.Label(time_input_frame, text="終了時間 (1-24):").pack(anchor="w", pady=(5,0))
        self.end_hour_entry = ttk.Entry(time_input_frame, width=5)
        self.end_hour_entry.pack(anchor="w")
        # Enterキーでスケジュール設定を実行
        self.end_hour_entry.bind("<Return>", lambda event: self.set_schedule_gui())


        set_schedule_button = ttk.Button(time_input_frame, text="スケジュールを設定/追加", command=self.set_schedule_gui)
        set_schedule_button.pack(pady=10)

        clear_schedule_button = ttk.Button(time_input_frame, text="選択メンバーのスケジュールをクリア", command=self.clear_schedule_gui)
        clear_schedule_button.pack()

        # ガントチャート表示エリア
        chart_frame = ttk.LabelFrame(main_frame, text="在宅スケジュール (ガントチャート)", padding="10")
        chart_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # ChartCanvasウィジェットのインスタンス化
        # DataManagerと、チャート更新後に必要であれば実行されるコールバックを渡す
        self.chart_canvas = ChartCanvas(chart_frame, self.data_manager, self.chart_update_callback)
        self.chart_canvas.pack(fill=tk.BOTH, expand=True)

    def chart_update_callback(self):
        """
        ガントチャート側でデータが変更された際に呼び出されるコールバック。
        必要に応じて、他のGUI要素（例: メンバーリストボックス）を更新する。
        """
        # 現在はこのコールバックで特別なGUI更新は不要だが、将来的な拡張のために残しておく
        pass

    def load_initial_data_into_listbox(self):
        """
        アプリケーション起動時にDataManagerからメンバー名をロードし、
        メンバーリストボックスに表示する。
        """
        self.member_listbox.delete(0, tk.END) # 既存の項目をクリア
        for name in self.data_manager.family_members.keys():
            self.member_listbox.insert(tk.END, name)

    def add_member_gui(self):
        """
        GUIからのメンバー追加要求を処理する。
        DataManagerを介してメンバーを追加し、UIを更新する。
        """
        name = self.member_name_entry.get().strip()
        if not name:
            messagebox.showwarning("入力エラー", "メンバー名を入力してください。", parent=self)
            return
        
        success, message = self.data_manager.add_member(name)
        if success:
            self.member_listbox.insert(tk.END, name)
            messagebox.showinfo("成功", message, parent=self)
            self.chart_canvas.update_gantt_chart() # チャートを再描画
        else:
            messagebox.showinfo("情報", message, parent=self) # 既に存在する場合など
        self.member_name_entry.delete(0, tk.END)
        self.member_name_entry.focus_set()

    def delete_member_gui(self):
        """
        GUIからのメンバー削除要求を処理する。
        選択されたメンバーをDataManagerを介して削除し、UIを更新する。
        """
        selected_indices = self.member_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("選択エラー", "削除するメンバーをリストから選択してください。", parent=self)
            return
            
        member_index = selected_indices[0]
        name_to_delete = self.member_listbox.get(member_index)

        if messagebox.askyesno("確認", f"本当に '{name_to_delete}' を削除しますか？\nこの操作は元に戻せません。", parent=self):
            success, message = self.data_manager.delete_member(name_to_delete)
            if success:
                self.member_listbox.delete(member_index)
                messagebox.showinfo("成功", message, parent=self)
                self.chart_canvas.update_gantt_chart() # チャートを再描画
            else:
                messagebox.showerror("エラー", message, parent=self)

    def set_schedule_gui(self):
        """
        GUIからのスケジュール設定/追加要求を処理する。
        DataManagerを介してスケジュールを追加し、UIを更新する。
        """
        selected_indices = self.member_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("選択エラー", "スケジュールを設定するメンバーをリストから選択してください。", parent=self)
            return
            
        member_index = selected_indices[0]
        name = self.member_listbox.get(member_index)

        try:
            start_hour = int(self.start_hour_entry.get())
            end_hour = int(self.end_hour_entry.get())
        except ValueError:
            messagebox.showwarning("入力エラー", "開始時間と終了時間は数字で入力してください。", parent=self)
            return

        if not (0 <= start_hour <= 23 and 0 <= end_hour <= 24 and start_hour < end_hour):
            messagebox.showwarning("入力エラー", "時間は0から24の整数で、開始時間は終了時間より小さくしてください。\n例: 9時から17時まで家にいる場合 -> 開始: 9, 終了: 17", parent=self)
            return
            
        success, message = self.data_manager.add_schedule(name, start_hour, end_hour)
        if success:
            messagebox.showinfo("成功", message, parent=self)
            self.chart_canvas.update_gantt_chart() # チャートを再描画
        else:
            messagebox.showerror("エラー", message, parent=self)

        self.start_hour_entry.delete(0, tk.END)
        self.end_hour_entry.delete(0, tk.END)
        self.start_hour_entry.focus_set()

    def clear_schedule_gui(self):
        """
        GUIからのスケジュールクリア要求を処理する。
        選択されたメンバーの全スケジュールをDataManagerを介してクリアし、UIを更新する。
        """
        selected_indices = self.member_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("選択エラー", "スケジュールをクリアするメンバーをリストから選択してください。", parent=self)
            return
            
        member_index = selected_indices[0]
        name = self.member_listbox.get(member_index)

        if messagebox.askyesno("確認", f"本当に '{name}' のスケジュールをすべてクリアしますか？", parent=self):
            success, message = self.data_manager.clear_member_schedules(name)
            if success:
                messagebox.showinfo("成功", message, parent=self)
                self.chart_canvas.update_gantt_chart() # チャートを再描画
            else:
                messagebox.showerror("エラー", message, parent=self)

    def on_closing(self):
        """
        アプリケーション終了時の処理。
        DataManagerを介してデータを保存し、ウィンドウを破棄する。
        """
        if messagebox.askokcancel("終了", "アプリケーションを終了しますか？\nデータは自動的に保存されます。", parent=self):
            self.data_manager.save_data() # データを保存
            self.destroy() # ウィンドウを破棄
