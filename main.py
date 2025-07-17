# main.py
import os
from gui.app import ScheduleApp

def main():
    """
    アプリケーションのメインエントリポイント。
    データディレクトリの作成と、Tkinterアプリケーションの起動を行う。
    """
    # データファイルを保存するディレクトリが存在しない場合は作成
    if not os.path.exists('data'):
        os.makedirs('data')

    # ScheduleAppクラスのインスタンスを作成し、Tkinterのメインループを開始
    app = ScheduleApp()
    app.mainloop()

if __name__ == "__main__":
    main()
