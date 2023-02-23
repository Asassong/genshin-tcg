# genshin-tcg
原神七圣召唤/Genius Invokation TCG

即将完成/Close to completion

Demo is released，can see at [bilibili](https://www.bilibili.com/video/BV1xA411z78T/), [youtube](https://youtu.be/gqJ6eA0M9xs)

## 已重构

> 整局游戏用同一个种子生成的随机数序列

> 记录玩家操作

> 将多玩家同时进行的操作改为异步

> 逻辑上部分支持多玩家(具体逻辑待设计）

> modify存放容器重回list

> 将状态和modify分开，更清晰的modify管理

> 将invoke modify与preview cost，preview damage分开，invoke modify时即时触发效果和消耗次数。

## Roadmap

> **(目前进度)** 重构中

> 天赋卡

> 事件触发器(maybe, 如果没有其他办法的话）

> 战斗时限制条件检验

* v1.0 程序逻辑运行如官服

> 将服务端改为多进程多线程（现在为单进程多线程）

> 将传输协议改为KCP

* v2.0 卡牌编辑器，自定义牌局

* v2.x 强化学习/Reinforcement learning

## 致谢

* ChatGPT

