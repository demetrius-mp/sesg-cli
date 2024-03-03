import os
from datetime import datetime

from dotenv import load_dotenv
from telebot import TeleBot


load_dotenv()


class TelegramReport:
    def __init__(self, slr_name: str, experiment_name: str, strategies: list[tuple[str, str]]):
        self._sesg_checkpoint_bot = TeleBot(
            token=str(os.environ.get('TELEGRAM_TOKEN')),
            parse_mode="HTML"
        )
        self._chat_id = os.environ.get('TELEGRAM_CHAT_ID')

        self.slr_name: str = slr_name
        self.experiment_name: str = experiment_name
        self.strategies: list[tuple[str, str]] = strategies

    @staticmethod
    def get_execution_time(execution_time: float) -> tuple:
        """
        Gets the hours, minutes and seconds of the given execution time in milliseconds
        for better visualization by the user.

        Args:
            execution_time: time passed in milliseconds.

        Returns: a tuple with hours, minutes and seconds converted.

        """
        hours = int(execution_time // 3600)
        minutes = int((execution_time % 3600) // 60)
        seconds = int(execution_time % 60)

        return hours, minutes, seconds

    def send_new_execution_report(self) -> None:
        """
        Report for a new experiment running. (`sesg experiment start`)
        """
        message = f"\U00002705Starting <b>{self.experiment_name}</b> execution\U00002705\n\n" \
                  f"<b>Strategies</b>: {self.strategies}\n" \
                  f"<b>Slr</b>: {self.slr_name}\n" \
                  f"<b>Datetime</b>: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}\n" \
                  f"<b>PC specs</b>: {os.environ.get('PC_SPECS')}"

        self._sesg_checkpoint_bot.send_message(
            chat_id=str(self._chat_id), text=message)

    def send_new_strategy_start_report(self, strategy: str) -> None:
        """
        Report for a new strategy starting its execution.

        Args:
            strategy: which strategy is starting. (e.g., lda, bertopic)
        """
        message = f"\U0001F7E2Starting <b>{strategy}</b>\U0001F7E2\n\n" \
                  f"<b>Experiment</b>: {self.experiment_name}\n" \
                  f"<b>Slr</b>: {self.slr_name}\n" \
                  f"<b>Percentage</b>: 0%\n"

        self._sesg_checkpoint_bot.send_message(
            chat_id=str(self._chat_id), text=message)

    def send_progress_report(self, strategy: str, percentage: int, exec_time: float) -> None:
        """
        Report of the experiment progress (it's triggered every quarter of the total execution
        of each strategy).

        Args:
            strategy: which strategy is being executed.
            percentage: what percentage the execution at
            exec_time: total execution time passed.
        """
        hours, minutes, seconds = self.get_execution_time(exec_time)
        message = f"\U0001F7E1Running <b>{strategy}</b>...\U0001F7E1\n\n" \
                  f"<b>Experiment</b>: {self.experiment_name}\n" \
                  f"<b>Slr</b>: {self.slr_name}\n" \
                  f"<b>Percentage</b>: {percentage}%\n" \
                  f"<b>Current execution time</b>: {hours}:{minutes}:{seconds}\n"

        self._sesg_checkpoint_bot.send_message(
            chat_id=str(self._chat_id), text=message)

    def send_finish_report(self, exec_time: float) -> None:
        """
        End of the execution report.

        Args:
            exec_time: total execution time passed.
        """
        hours, minutes, seconds = self.get_execution_time(exec_time)
        message = f"\U0001F534Finished <b>{self.experiment_name}</b> execution\U0001F534\n\n" \
                  f"<b>Slr</b>:{self.slr_name}\n" \
                  f"<b>Datetime</b>:{datetime.now().strftime('%d-%m-%Y %H:%M:%S')}\n" \
                  f"<b>Execution total time</b>: {hours}:{minutes}:{seconds}\n"

        self._sesg_checkpoint_bot.send_message(
            chat_id=str(self._chat_id), text=message)

    def send_error_report(self, error_message: str) -> None:
        """
        Error report.
        Args:
            error_message: error message raised.
        """
        message = f"\U000026A0Error <b>{self.experiment_name}</b> execution\U000026A0\n\n" \
                  f"<b>Slr</b>: {self.slr_name}\n" \
                  f"<b>Datetime</b>: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}\n" \
                  f"<b>Error message</b>: {error_message}\n"

        self._sesg_checkpoint_bot.send_message(
            chat_id=str(self._chat_id), text=message)