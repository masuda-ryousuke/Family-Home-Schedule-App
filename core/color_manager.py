# core/color_manager.py

class ColorManager:
    """
    アプリケーションで使用する色を管理し、新しいメンバーに循環的に色を割り当てるクラス。
    """
    CHART_COLORS = [
        "skyblue", "lightgreen", "salmon", "orchid", "gold",
        "lightcoral", "lightsteelblue", "palegreen", "sandybrown", "plum"
    ]
    
    def __init__(self):
        """
        ColorManagerのコンストラクタ。
        現在の色割り当てインデックスを初期化する。
        """
        self.current_color_index = 0

    def get_next_color(self):
        """
        CHART_COLORSリストから次の色を取得し、インデックスを更新する。
        リストの最後まで到達したら最初に戻る（循環）。
        :return: 次に割り当てる色 (文字列)
        """
        color = self.CHART_COLORS[self.current_color_index]
        self.current_color_index = (self.current_color_index + 1) % len(self.CHART_COLORS)
        return color

    def set_current_color_index_based_on_used_colors(self, used_colors):
        """
        ロードされたデータで使用されている色を考慮して、
        次に割り当てる色のインデックスを適切に設定する。
        :param used_colors: 既にデータで使用されている色のセット
        """
        self.current_color_index = 0
        # まだ使われていない最初の色を見つける
        while self.current_color_index < len(self.CHART_COLORS) and \
              self.CHART_COLORS[self.current_color_index] in used_colors:
            self.current_color_index += 1
        
        # もし全てのCHART_COLORSが使われていたら、最初の色から再利用
        if self.current_color_index >= len(self.CHART_COLORS):
            self.current_color_index = 0
