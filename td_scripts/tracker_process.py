"""Own the opt-in hand tracker started from the TouchDesigner panel."""

from pathlib import Path
import subprocess
from time import monotonic
from uuid import uuid4


class TrackerProcess:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.python = self.folder / '.venv-gesture' / 'Scripts' / 'python.exe'
        self.model = self.folder / 'assets' / 'models' / 'hand_landmarker.task'
        self.log = self.folder / '.local' / 'hand-tracker.log'
        self.process = None
        self.stop_file = None
        self.stop_deadline = None
        self.log_offset = 0

    @property
    def running(self):
        return self.process is not None

    @property
    def stopping(self):
        return self.stop_deadline is not None

    def check_setup(self):
        if not self.python.is_file():
            raise RuntimeError('Hand tracker environment is missing. Run scripts/setup_windows.ps1.')
        if not self.model.is_file():
            raise RuntimeError('Hand Landmarker model is missing. Run scripts/setup_windows.ps1.')

    def start(self, port):
        self.check_setup()
        if self.running:
            return
        self.log.parent.mkdir(parents=True, exist_ok=True)
        stop_file = self.log.parent / f'hand-tracker-{uuid4().hex}.stop'
        args = [str(self.python), '-u', '-m', 'gesture_service.main', '--mode', 'VISION',
                '--port', str(port), '--stop-file', str(stop_file)]
        with self.log.open('ab') as log:
            log.write(b'\n--- Hand tracker start ---\n')
            log.flush()
            self.log_offset = log.tell()
            self.process = subprocess.Popen(
                args, cwd=self.folder, stdin=subprocess.DEVNULL,
                stdout=log, stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            )
        self.stop_file = stop_file

    def stop(self):
        if not self.running or self.stopping:
            return
        self.stop_deadline = monotonic() + 4.0
        if self.process.poll() is None:
            try:
                self.stop_file.touch()
            except OSError:
                self.process.terminate()

    def poll(self, now):
        """Return a status message when the owned process exits."""
        if not self.running:
            return ''
        code = self.process.poll()
        if code is None:
            if self.stopping and now >= self.stop_deadline:
                self.process.kill()
            return ''
        stopping = self.stopping
        self.process = None
        self.stop_deadline = None
        self.stop_file.unlink(missing_ok=True)
        self.stop_file = None
        if stopping:
            return 'Hand tracker stopped.'
        try:
            with self.log.open('rb') as log:
                log.seek(max(self.log_offset, self.log.stat().st_size - 4096))
                lines = log.read().decode('utf-8', errors='replace').splitlines()
            detail = next((line.strip() for line in reversed(lines) if line.strip()), '')
        except OSError:
            detail = ''
        prefix = f'Hand tracker exited ({code}).'
        return f'{prefix} {detail[:140]} See .local/hand-tracker.log.'
