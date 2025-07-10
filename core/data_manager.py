# core/data_manager.py
import json
import os
from core.color_manager import ColorManager # 色管理モジュールをインポート

class DataManager:
    """
    アプリケーションのデータを管理するクラス。
    家族メンバー、スケジュール、色の割り当てに関するデータのロード、保存、操作を行う。
    """
    DATA_FILE = 'data/data.json' # データファイルのパス（dataディレクトリ内）

    def __init__(self):
        """
        DataManagerのコンストラクタ。
        ColorManagerを初期化し、既存のデータをロードする。
        """
        self.family_members = {} # 家族メンバーとそのスケジュールを保持する辞書
        self.color_manager = ColorManager() # 色管理クラスのインスタンス
        self.load_data()

    def load_data(self):
        """
        ファイルから家族メンバーとスケジュールデータをロードする。
        データファイルが存在しない場合は、新しいデータとして初期化される。
        """
        if os.path.exists(self.DATA_FILE):
            try:
                with open(self.DATA_FILE, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    self.family_members = {} # ロード前に既存データをクリア

                    used_colors = set() # ロードされたデータで使用されている色を追跡
                    for name, data in loaded_data.items():
                        schedules_list = data.get('schedules', [])
                        color = data.get('color')
                        # 保存データに色がない、または無効な色の場合、新しい色を割り振る
                        if color is None or color not in self.color_manager.CHART_COLORS:
                            color = self.color_manager.get_next_color()
                        self.family_members[name] = {
                            'schedules': [tuple(s) for s in schedules_list],
                            'color': color
                        }
                        used_colors.add(color)
                    
                    # 使用済みの色に基づいて、次の色割り当てのインデックスを適切に設定
                    self.color_manager.set_current_color_index_based_on_used_colors(used_colors)
                        
                print(f"データが '{self.DATA_FILE}' からロードされました。")
            except json.JSONDecodeError as e:
                # ファイルが破損している場合などのJSONデコードエラー
                print(f"エラー: データファイルの読み込みに失敗しました。ファイルが破損している可能性があります: {e}")
                self.family_members = {} # データ破損時は空のデータで開始
            except Exception as e:
                # その他の予期せぬエラー
                print(f"エラー: データロード中に予期せぬエラーが発生しました: {e}")
                self.family_members = {}
        else:
            print(f"データファイル '{self.DATA_FILE}' が見つかりませんでした。新しいデータを作成します。")

    def save_data(self):
        """
        現在の家族メンバーとスケジュールデータをファイルに保存する。
        """
        try:
            serializable_data = {}
            for name, data in self.family_members.items():
                serializable_data[name] = {
                    'schedules': list(data['schedules']), # タプルをリストに変換して保存
                    'color': data['color']
                }

            with open(self.DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(serializable_data, f, ensure_ascii=False, indent=4) # 整形して保存
            print(f"データが '{self.DATA_FILE}' に保存されました。")
        except Exception as e:
            print(f"エラー: データ保存中にエラーが発生しました: {e}")

    def add_member(self, name):
        """
        新しい家族メンバーを追加する。
        :param name: 追加するメンバーの名前
        :return: (成功フラグ, メッセージ)
        """
        if name in self.family_members:
            return False, f"'{name}' は既に登録されています。"
        else:
            self.family_members[name] = {'schedules': [], 'color': self.color_manager.get_next_color()}
            self.save_data() # 変更を保存
            return True, f"'{name}' を家族に追加しました。"

    def delete_member(self, name):
        """
        指定された家族メンバーを削除する。
        :param name: 削除するメンバーの名前
        :return: (成功フラグ, メッセージ)
        """
        if name in self.family_members:
            del self.family_members[name]
            self.save_data() # 変更を保存
            return True, f"'{name}' を削除しました。"
        return False, f"'{name}' が見つかりませんでした。"

    def add_schedule(self, member_name, start_hour, end_hour):
        """
        指定されたメンバーに新しいスケジュールを追加する。
        :param member_name: スケジュールを追加するメンバーの名前
        :param start_hour: 開始時間 (整数)
        :param end_hour: 終了時間 (整数)
        :return: (成功フラグ, メッセージ)
        """
        if member_name not in self.family_members:
            return False, f"メンバー '{member_name}' が見つかりません。"
        
        self.family_members[member_name]['schedules'].append((start_hour, end_hour))
        self.family_members[member_name]['schedules'].sort() # スケジュールを時間順にソート
        self.save_data() # 変更を保存
        return True, f"'{member_name}' のスケジュールに {start_hour}時から{end_hour}時を追加しました。"

    def clear_member_schedules(self, member_name):
        """
        指定されたメンバーの全てのスケジュールをクリアする。
        :param member_name: スケジュールをクリアするメンバーの名前
        :return: (成功フラグ, メッセージ)
        """
        if member_name not in self.family_members:
            return False, f"メンバー '{member_name}' が見つかりません。"
        self.family_members[member_name]['schedules'] = [] # スケジュールリストを空にする
        self.save_data() # 変更を保存
        return True, f"'{member_name}' のスケジュールをすべてクリアしました。"

    def update_schedule(self, member_name, old_schedule, old_index, new_schedule):
        """
        メンバーの既存のスケジュールを新しいスケジュールで更新する。
        :param member_name: スケジュールを更新するメンバーの名前
        :param old_schedule: 更新前のスケジュール (タプル)
        :param old_index: old_scheduleがfamily_members[member_name]['schedules']内の何番目の要素か
        :param new_schedule: 更新後のスケジュール (タプル)
        :return: (成功フラグ, メッセージ)
        """
        if member_name not in self.family_members:
            return False, f"エラー: メンバー '{member_name}' が見つかりません。"

        schedules = self.family_members[member_name]['schedules']
        try:
            # 元のインデックスが有効範囲内で、かつ内容が一致する場合のみ削除
            if old_index < len(schedules) and schedules[old_index] == old_schedule:
                del schedules[old_index]
            else:
                # インデックスが無効または内容が一致しない場合は、値で検索して削除
                # （ドラッグ中に他のスケジュールが追加/削除された場合など）
                schedules.remove(old_schedule)
            
            schedules.append(new_schedule) # 新しいスケジュールを追加
            schedules.sort() # ソート
            self.save_data() # 変更を保存
            return True, "スケジュールが更新されました。"
        except ValueError:
            return False, f"元のスケジュール {old_schedule} が見つかりませんでした。データが変更された可能性があります。"
        except Exception as e:
            return False, f"スケジュールの更新中にエラーが発生しました: {e}"

    def delete_schedule(self, member_name, schedule_to_delete, original_index):
        """
        メンバーの特定のスケジュールを削除する。
        :param member_name: スケジュールを削除するメンバーの名前
        :param schedule_to_delete: 削除するスケジュール (タプル)
        :param original_index: original_scheduleがfamily_members[member_name]['schedules']内の何番目の要素か
        :return: (成功フラグ, メッセージ)
        """
        if member_name not in self.family_members:
            return False, f"メンバー '{member_name}' が見つかりません。"

        schedules = self.family_members[member_name]['schedules']
        try:
            # 元のインデックスが有効範囲内で、かつ内容が一致する場合のみ削除
            if original_index < len(schedules) and schedules[original_index] == schedule_to_delete:
                del schedules[original_index]
            else:
                # インデックスが無効または内容が一致しない場合は、値で検索して削除
                schedules.remove(schedule_to_delete)
            self.save_data() # 変更を保存
            return True, f"'{member_name}' のスケジュール {schedule_to_delete[0]}時-{schedule_to_delete[1]}時 を削除しました。"
        except ValueError:
            return False, "削除するスケジュールが見つかりませんでした。データが変更された可能性があります。"
        except Exception as e:
            return False, f"スケジュールの削除中にエラーが発生しました: {e}"
