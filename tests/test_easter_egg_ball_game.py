import sys
import unittest
from pathlib import Path

from PySide6.QtCore import QRect
from PySide6.QtWidgets import QApplication, QWidget


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pypad.ui.main_window.misc import MiscMixin


class _GamificationStub:
    def __init__(self) -> None:
        self._state = {}

    def state(self) -> dict:
        return self._state


class _BallHost(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.settings = {"sound_enabled": False}
        self.gamification = _GamificationStub()

    def _easter_egg_ball_state(self) -> dict:
        state = self.gamification.state()
        ball_state = state.setdefault("easter_egg_ball", {})
        ball_state.setdefault("best_score", 0)
        ball_state.setdefault("best_combo", 0)
        ball_state.setdefault("leaderboard", [])
        ball_state.setdefault("skins_unlocked", ["#ff8a00"])
        ball_state.setdefault("backgrounds_unlocked", ["Midnight Grid"])
        ball_state.setdefault("trails_unlocked", ["Classic"])
        ball_state.setdefault("equipped_skin", "#ff8a00")
        ball_state.setdefault("equipped_background", "Midnight Grid")
        ball_state.setdefault("equipped_trail", "Classic")
        ball_state.setdefault("message_score", 42)
        ball_state.setdefault("message_text", "test")
        return ball_state

    def _unlock_easter_egg(self, title: str, message: str) -> None:
        return None


class EasterEggBallGameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_obstacle_collision_resolves_overlap(self) -> None:
        host = _BallHost()
        host.resize(640, 480)
        game = MiscMixin._EasterEggBallGame(host, "score")
        game.resize(640, 480)
        game._timer.stop()

        game._obstacles = [
            {
                "x": 180.0,
                "y": 120.0,
                "w": 24.0,
                "h": 120.0,
                "vx": 0.0,
                "vy": 0.0,
            }
        ]
        game._pos_x = 176.0
        game._pos_y = 150.0
        game._vel_x = 6.0
        game._vel_y = 0.0

        game._tick()
        damage_after_first_tick = game._damage_count

        ball_rect = QRect(int(game._pos_x), int(game._pos_y), game._diameter, game._diameter)
        obstacle = game._obstacles[0]
        obstacle_rect = QRect(int(obstacle["x"]), int(obstacle["y"]), int(obstacle["w"]), int(obstacle["h"]))

        self.assertFalse(ball_rect.intersects(obstacle_rect))
        self.assertEqual(damage_after_first_tick, 1)

        game._tick()

        ball_rect = QRect(int(game._pos_x), int(game._pos_y), game._diameter, game._diameter)
        self.assertFalse(ball_rect.intersects(obstacle_rect))
        self.assertEqual(game._damage_count, damage_after_first_tick)


if __name__ == "__main__":
    unittest.main()
