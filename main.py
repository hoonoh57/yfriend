#!/usr/bin/env python3
"""
main.py - yFriend prototype entry point
Usage: python main.py "video topic"
"""
from __future__ import annotations

import asyncio
import sys

from core.orchestrator import Orchestrator


async def main():
    if len(sys.argv) < 2:
        print('Usage: python main.py "video topic"')
        print('Example: python main.py "Why Korean four seasons are beautiful"')
        sys.exit(1)

    topic = sys.argv[1]
    orchestrator = Orchestrator()
    project_dir = await orchestrator.run(topic)
    print(f"\nResult: {project_dir / '06_assembly' / 'final_prototype.mp4'}")


if __name__ == "__main__":
    asyncio.run(main())