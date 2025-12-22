# Cache模块设计说明

## 项目概述
本项目实现了一个2路组相联的Cache模块，用于计算机体系结构课程实验四。

## Cache设计规格
- **组相联度**：2路组相联
- **每路大小**：4KB (4096字节)
- **Cache总大小**：8KB
- **Cache行大小**：16字节 (128位，4个字)
- **组数**：256组 (每路)
- **替换算法**：LRU (Least Recently Used)
- **地址划分**：
  - Tag: addr[31:12] (20位)
  - Index: addr[11:4] (8位)
  - Offset: addr[3:0] (4位)

## 模块接口
模块接口完全按照表10-4的规范设计，包括：
1. **Cache与CPU流水线的交互接口**
   - valid, op, index, tag, offset, wstrb, wdata (输入)
   - addr_ok, data_ok, rdata (输出)

2. **Cache与AXI总线接口的交互接口**
   - rd_req, rd_type, rd_addr (读请求输出)
   - rd_rdy, ret_valid, ret_last, ret_data (读响应输入)
   - wr_req, wr_type, wr_addr, wr_wstrb, wr_data (写请求输出)
   - wr_rdy (写响应输入)

## 状态机设计
Cache模块采用5状态状态机：

1. **IDLE**: 空闲状态，等待访问请求
2. **LOOKUP**: 查找状态，判断Cache命中或缺失
3. **MISS**: 缺失状态，判断是否需要替换
4. **REPLACE**: 替换状态，将脏数据写回主存
5. **REFILL**: 重填状态，从主存读取新的Cache行

## 核心实现特点

### 1. 存储结构
- 使用数组实现TagV RAM和Data RAM
- 每路包含256个Cache行
- 每个Cache行包含：Valid位、20位Tag、128位Data

### 2. LRU替换算法
- 为每个组维护一个LRU位
- LRU=0表示Way0最近使用，替换Way1
- LRU=1表示Way1最近使用，替换Way0
- 命中时更新LRU位
- Refill时更新LRU位

### 3. 读操作流程
1. IDLE状态接收读请求
2. LOOKUP状态查找Cache
3. 如果命中，直接返回数据
4. 如果缺失，进入MISS状态
5. 判断是否需要写回（REPLACE状态）
6. 从主存读取数据（REFILL状态）
7. 返回LOOKUP重新查找

### 4. 写操作流程
1. IDLE状态接收写请求
2. LOOKUP状态查找Cache
3. 如果命中，直接写入Cache（Write Through）
4. 如果缺失，流程同读操作

### 5. 硬件初始化
- 使用initial块初始化所有TagV为0（无效）
- 推荐使用硬件初始化，符合实验要求

## 文件说明
- `cache.v`: Cache模块的主要实现文件
- 位置：`cache_verify/rtl/cache/cache.v`

## 在Vivado中运行步骤

### 1. 准备工作
确保lab16.zip已解压到不含中文的路径下。

### 2. 添加源文件

**重要**：确保cache.v文件位于正确位置：`<工程路径>/rtl/cache/cache.v`

1. 打开Vivado工程：`run_vivado/cache_verify/cache_verify.xpr`
2. 在Sources窗口中，右键点击"Design Sources"
3. 选择"Add Sources"
4. 选择"Add or create design sources"，点击Next
5. 点击"Add Files"按钮
6. 浏览到工程的`rtl/cache/`目录，选中`cache.v`文件
7. **重要**：勾选"Copy sources into project"（确保文件被复制到工程中）
8. 点击Finish
9. 在Sources窗口中确认能看到cache.v文件（应该在Design Sources下）

**验证添加成功**：
- 在Sources窗口的Design Sources中应该能看到：
  ```
  ├─ cache_top (cache_top.v)
  └─ cache (cache.v)
  ```
- 或者cache.v作为cache_top的子模块出现

### 3. 运行仿真
1. **关闭**之前打开的任何仿真窗口
2. 在Flow Navigator中，点击"Run Simulation" → "Run Behavioral Simulation"
3. 等待仿真启动（首次编译需要一些时间）
4. 观察仿真波形，检查Cache模块的行为

**如果仍然报错"Module <cache> not found"**：
- 检查cache.v文件是否真的在Sources列表中
- 尝试右键cache_top.v，选择"Set as Top"
- 重新添加cache.v，这次确保勾选"Copy sources into project"
- 如果还不行，关闭Vivado，删除仿真缓存文件夹，重新打开工程

### 4. 验证结果
1. 仿真会对每个Index发出读写请求
2. 观察七段数码管显示的test_index值
3. 检查仿真终端输出，确认没有错误
4. 如果仿真通过，说明Cache模块实现正确

### 5. 综合与实现（可选）
如果需要上板验证：
1. 点击"Run Synthesis"进行综合
2. 综合完成后，点击"Run Implementation"
3. 实现完成后，点击"Generate Bitstream"
4. 生成比特流文件后，可以下载到FPGA板进行测试

## 调试建议
1. 如果仿真出错，检查以下几点：
   - 状态机转换是否正确
   - AXI握手信号是否正确
   - 数据读写是否对齐
   - LRU更新逻辑是否正确

2. 使用Vivado的波形查看器：
   - 观察状态机状态转换
   - 检查命中/缺失信号
   - 验证读写数据的正确性

3. 常见问题：
   - 如果一直停在某个状态，检查状态转换条件
   - 如果读写数据不对，检查offset的使用
   - 如果AXI传输有问题，检查握手信号

## 设计考虑
1. **简化设计**：采用Write Through策略，命中时直接写入，不需要维护脏位
2. **性能优化**：使用LRU算法提高命中率
3. **可读性**：状态机清晰，代码结构分明
4. **可扩展性**：参数化设计，便于修改配置

## 作者
计算机体系结构课程实验 - 实验四

## 日期
2025年12月22日
