---
globs: ["**/*.py", "**/*.md"]
alwaysApply: false
description: "Code quality constraints: avoid anti-patterns and keep modular design"
---

# Code Quality Rules

## Design Principles

- 优先小函数、单一职责、清晰边界。
- 业务常量集中声明，避免分散 Hardcoded。
- 新逻辑优先复用现有模块，减少重复实现与耦合扩散。

## Anti-Patterns（Avoid）

- Magic Number / Magic String
- Hardcoded 业务关键值
- God Object
- Shotgun Surgery
- Spaghetti Code
- 其他明显降低可维护性的反模式

## Practical Checklist

- 常量是否已命名并集中管理？
- 新增模块是否职责单一、接口可测试？
- 是否通过拆分函数降低复杂度与圈复杂度？
- 是否避免为“临时通过”引入技术债？
