"""
Defines the interface for Quilchoom knowledge interpretation.
"""

from typing import Protocol

from quilchoom.domain.interpretation import InterpretationContext, InterpretationResult


class KnowledgeInterpreter(Protocol):
    def interpret(self, context: InterpretationContext) -> InterpretationResult: ...
