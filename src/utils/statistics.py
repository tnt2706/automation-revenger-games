from utils.mapping_utils import map_mode_check_display
from collections import defaultdict
from rich.console import Console


class GameStatistics:
    """Track test results by mode across all games"""

    def __init__(self):
        self.results_by_mode = defaultdict(lambda: {"success": 0, "failed": 0})

    def add_result(self, mode: str, status: str):
        """Add a test result for a specific mode"""
        if status == "success":
            self.results_by_mode[mode]["success"] += 1
        else:
            self.results_by_mode[mode]["failed"] += 1

    def print_final_summary(self, console: Console):
        """Print final summary by mode"""
        console.print(f"\n[bold blue]📊 Final Results Summary:[/bold blue]")

        for mode, results in self.results_by_mode.items():
            display_mode = map_mode_check_display(mode)
            total = results["success"] + results["failed"]
            success_rate = (results["success"] / total * 100) if total > 0 else 0

            console.print(
                f"🔧 {display_mode}: "
                f"[green]{results['success']} ✅[/green] / "
                f"[red]{results['failed']} ❌[/red] "
                f"({success_rate:.1f}% success rate)"
            )
