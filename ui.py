from collections.abc import Iterable, Iterator, Sequence
from typing import Any

import questionary
from questionary.prompts.common import Choice, InquirerControl
from rich.status import Status

__all__ = ('progress_bar',)

type ChoiceSequence = Sequence[str | Choice | dict[str, Any]]


class IterativeInquirerControl(InquirerControl):
    def __init__(self, choices: ChoiceSequence | Iterator | tuple[Iterable, Iterator], *args, **kwargs):
        choice_prefix = []

        if len(choices) == 2 and isinstance(choices[0], Iterable) and isinstance(choices[1], Iterator):  # noqa: PLR2004
            choice_prefix, choices = choices

        self.WINDOW_SIZE = (len(choice_prefix) // 10 + 1) * 10

        if isinstance(choices, Iterator):
            initial_choices = choice_prefix + [str(next(choices)) for _ in range(self.WINDOW_SIZE - len(choice_prefix))]
            self.continuation_stream = choices
        else:
            initial_choices = choices
            self.continuation_stream = None

        self.trace = initial_choices
        self.trace_index = 0

        super().__init__(initial_choices, *args[1:], **kwargs)

    def select_previous(self) -> None:
        if self.continuation_stream is not None and self.pointed_at == 0:
            if self.trace_index == 0:
                return

            new_window = self.trace[self.trace_index - 1:self.trace_index + self.WINDOW_SIZE - 1]
            self.choices = [Choice.build(c) for c in new_window]
        else:
            self.pointed_at = (self.pointed_at - 1) % self.choice_count

        self.trace_index -= 1

    def select_next(self) -> None:
        if self.continuation_stream is not None:
            if self.trace_index == len(self.trace) - self.WINDOW_SIZE:
                self.trace.append(str(next(self.continuation_stream)))

            if self.pointed_at == self.choice_count - 1:
                new_window = self.trace[self.trace_index + 1:self.trace_index + self.WINDOW_SIZE + 1]
                self.choices = [Choice.build(c) for c in new_window]

        self.pointed_at = (self.pointed_at + 1) % self.choice_count
        self.trace_index += 1


class ProgressBar(Status):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.previous_status = self.status

    def update(self, *args, **kwargs):
        self.previous_status = self.status
        super().update(*args, **kwargs)

    def revert_status(self):
        self.update(self.previous_status)


questionary.prompts.select.InquirerControl = IterativeInquirerControl

progress_bar = ProgressBar('Initializing...', spinner='dots2')
