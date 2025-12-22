module cache(
    input         clk_g,
    input         resetn,
    
    // Cache与CPU流水线的交互接口
    input         valid,      // 表明请求有效
    input         op,         // 1: WRITE, 0: READ
    input  [ 7:0] index,      // 地址的index域 (addr[11:4])
    input  [19:0] tag,        // 地址的tag域 (addr[31:12])
    input  [ 3:0] offset,     // 地址的offset域 (addr[3:0])
    input  [ 3:0] wstrb,      // 写字节使能信号
    input  [31:0] wdata,      // 写数据
    output        addr_ok,    // 该次请求的地址传输OK，读：地址被接收；写：地址和数据都被接收
    output        data_ok,    // 该次请求的数据传输OK，读：数据返回；写：数据写入完成
    output [31:0] rdata,      // 读Cache的结果
    
    // Cache与AXI总线接口的交互接口
    output        rd_req,     // 读请求有效信号，高电平有效
    output [ 2:0] rd_type,    // 读请求类型，3'b000：字节，3'b001：半字，3'b010：字，3'b100：Cache行
    output [31:0] rd_addr,    // 读请求起始地址
    input         rd_rdy,     // 读请求能否被接收的握手信号，高电平有效
    input         ret_valid,  // 返回数据有效，高电平有效
    input         ret_last,   // 返回数据是一次读请求对应的最后一个返回数据
    input  [31:0] ret_data,   // 读返回数据
    output        wr_req,     // 写请求有效信号，高电平有效
    output [ 2:0] wr_type,    // 写请求类型，3'b000：字节，3'b001：半字，3'b010：字，3'b100：Cache行
    output [31:0] wr_addr,    // 写请求起始地址
    output [ 3:0] wr_wstrb,   // 写操作的字节掩码，仅在写请求类型为3'b000、3'b001、3'b010的情况下才有意义
    output[127:0] wr_data,    // 写数据
    input         wr_rdy      // 写请求能否被接收的握手信号，高电平有效
);

// Cache配置参数
localparam WAY_NUM = 2;           // 2路组相联
localparam CACHE_SIZE = 4096;     // 每路4KB
localparam LINE_SIZE = 16;        // Cache行大小16字节(4个字)
localparam SET_NUM = CACHE_SIZE / LINE_SIZE;  // 每路的组数 = 256
localparam INDEX_WIDTH = 8;       // index位宽
localparam OFFSET_WIDTH = 4;      // offset位宽
localparam TAG_WIDTH = 20;        // tag位宽

// 状态机定义
localparam IDLE    = 5'b00001;
localparam LOOKUP  = 5'b00010;
localparam MISS    = 5'b00100;
localparam REPLACE = 5'b01000;
localparam REFILL  = 5'b10000;

// TagV RAM和Data RAM的定义
// Way 0
reg                  tagv_way0 [SET_NUM-1:0];  // Valid位
reg  [TAG_WIDTH-1:0] tag_way0  [SET_NUM-1:0];  // Tag
reg  [127:0]         data_way0 [SET_NUM-1:0];  // Data (128位=16字节=4个字)

// Way 1
reg                  tagv_way1 [SET_NUM-1:0];  // Valid位
reg  [TAG_WIDTH-1:0] tag_way1  [SET_NUM-1:0];  // Tag
reg  [127:0]         data_way1 [SET_NUM-1:0];  // Data

// LRU位：0表示Way0最近使用，1表示Way1最近使用
reg lru [SET_NUM-1:0];

// 状态寄存器
reg [4:0] state;
reg [4:0] next_state;

// 请求寄存器
reg        req_op;
reg [ 7:0] req_index;
reg [19:0] req_tag;
reg [ 3:0] req_offset;
reg [ 3:0] req_wstrb;
reg [31:0] req_wdata;

// Hit判断
wire hit_way0;
wire hit_way1;
wire cache_hit;
wire hit_write;

assign hit_way0 = tagv_way0[req_index] && (tag_way0[req_index] == req_tag);
assign hit_way1 = tagv_way1[req_index] && (tag_way1[req_index] == req_tag);
assign cache_hit = hit_way0 || hit_way1;
assign hit_write = cache_hit && req_op;

// 替换选择：使用LRU
wire replace_way;  // 0: 替换way0, 1: 替换way1
// lru位记录最近使用的路：0表示way0最近使用，1表示way1最近使用
// 需要替换的路应当是“非最近使用”的那一路
assign replace_way = ~lru[req_index];

// Refill计数器
reg [1:0] refill_cnt;

// 读取的数据
reg [127:0] hit_data;
wire [31:0] load_data;

// 根据offset选择32位数据
assign load_data = (req_offset[3:2] == 2'b00) ? hit_data[31:0]   :
                   (req_offset[3:2] == 2'b01) ? hit_data[63:32]  :
                   (req_offset[3:2] == 2'b10) ? hit_data[95:64]  :
                                                 hit_data[127:96];

// 输出信号
reg        addr_ok_r;
reg        data_ok_r;
reg [31:0] rdata_r;
reg        rd_req_r;
reg [ 2:0] rd_type_r;
reg [31:0] rd_addr_r;
reg        wr_req_r;
reg [ 2:0] wr_type_r;
reg [31:0] wr_addr_r;
reg [ 3:0] wr_wstrb_r;
reg [127:0] wr_data_r;

assign addr_ok  = addr_ok_r;
assign data_ok  = data_ok_r;
assign rdata    = rdata_r;
assign rd_req   = rd_req_r;
assign rd_type  = rd_type_r;
assign rd_addr  = rd_addr_r;
assign wr_req   = wr_req_r;
assign wr_type  = wr_type_r;
assign wr_addr  = wr_addr_r;
assign wr_wstrb = wr_wstrb_r;
assign wr_data  = wr_data_r;

// 初始化
integer i;
initial begin
    for (i = 0; i < SET_NUM; i = i + 1) begin
        tagv_way0[i] = 1'b0;
        tag_way0[i]  = 20'b0;
        data_way0[i] = 128'b0;
        tagv_way1[i] = 1'b0;
        tag_way1[i]  = 20'b0;
        data_way1[i] = 128'b0;
        lru[i]       = 1'b0;
    end
end

// 状态机-时序逻辑
always @(posedge clk_g) begin
    if (!resetn) begin
        state <= IDLE;
    end else begin
        state <= next_state;
    end
end

// 状态机-组合逻辑
always @(*) begin
    case (state)
        IDLE: begin
            if (valid) begin
                next_state = LOOKUP;
            end else begin
                next_state = IDLE;
            end
        end
        
        LOOKUP: begin
            if (cache_hit) begin
                // 命中，完成后回到IDLE
                next_state = IDLE;
            end else begin
                // Cache miss
                next_state = MISS;
            end
        end
        
        MISS: begin
            // 判断是否需要写回
            if (replace_way == 1'b0) begin
                if (tagv_way0[req_index]) begin
                    // Way0有效，需要写回
                    next_state = REPLACE;
                end else begin
                    // Way0无效，直接Refill
                    next_state = REFILL;
                end
            end else begin
                if (tagv_way1[req_index]) begin
                    // Way1有效，需要写回
                    next_state = REPLACE;
                end else begin
                    // Way1无效，直接Refill
                    next_state = REFILL;
                end
            end
        end
        
        REPLACE: begin
            if (wr_req_r && wr_rdy) begin
                next_state = REFILL;
            end else begin
                next_state = REPLACE;
            end
        end
        
        REFILL: begin
            if (ret_valid && ret_last) begin
                next_state = LOOKUP;  // 回到LOOKUP重新查找
            end else begin
                next_state = REFILL;
            end
        end
        
        default: begin
            next_state = IDLE;
        end
    endcase
end

// 请求寄存器 - 在IDLE状态且valid有效时锁存
always @(posedge clk_g) begin
    if (!resetn) begin
        req_op     <= 1'b0;
        req_index  <= 8'b0;
        req_tag    <= 20'b0;
        req_offset <= 4'b0;
        req_wstrb  <= 4'b0;
        req_wdata  <= 32'b0;
    end else if (state == IDLE && valid) begin
        req_op     <= op;
        req_index  <= index;
        req_tag    <= tag;
        req_offset <= offset;
        req_wstrb  <= wstrb;
        req_wdata  <= wdata;
    end
end

// addr_ok信号：在LOOKUP状态产生（表示地址已接收）
always @(*) begin
    addr_ok_r = (state == LOOKUP);
end

// data_ok信号：读写完成时产生
always @(*) begin
    data_ok_r = (state == LOOKUP && cache_hit);
end

// 读数据 - 组合逻辑选择命中的way
always @(*) begin
    if (hit_way0) begin
        hit_data = data_way0[req_index];
    end else if (hit_way1) begin
        hit_data = data_way1[req_index];
    end else begin
        hit_data = 128'b0;
    end
end

// rdata输出 - 组合逻辑
always @(*) begin
    if (state == LOOKUP && cache_hit && !req_op) begin
        rdata_r = load_data;
    end else begin
        rdata_r = 32'b0;
    end
end

// Write操作
always @(posedge clk_g) begin
    if (state == LOOKUP && cache_hit && req_op) begin
        if (hit_way0) begin
            // 更新Way0的数据
            case (req_offset[3:2])
                2'b00: begin
                    if (req_wstrb[0]) data_way0[req_index][7:0]    <= req_wdata[7:0];
                    if (req_wstrb[1]) data_way0[req_index][15:8]   <= req_wdata[15:8];
                    if (req_wstrb[2]) data_way0[req_index][23:16]  <= req_wdata[23:16];
                    if (req_wstrb[3]) data_way0[req_index][31:24]  <= req_wdata[31:24];
                end
                2'b01: begin
                    if (req_wstrb[0]) data_way0[req_index][39:32]  <= req_wdata[7:0];
                    if (req_wstrb[1]) data_way0[req_index][47:40]  <= req_wdata[15:8];
                    if (req_wstrb[2]) data_way0[req_index][55:48]  <= req_wdata[23:16];
                    if (req_wstrb[3]) data_way0[req_index][63:56]  <= req_wdata[31:24];
                end
                2'b10: begin
                    if (req_wstrb[0]) data_way0[req_index][71:64]  <= req_wdata[7:0];
                    if (req_wstrb[1]) data_way0[req_index][79:72]  <= req_wdata[15:8];
                    if (req_wstrb[2]) data_way0[req_index][87:80]  <= req_wdata[23:16];
                    if (req_wstrb[3]) data_way0[req_index][95:88]  <= req_wdata[31:24];
                end
                2'b11: begin
                    if (req_wstrb[0]) data_way0[req_index][103:96]  <= req_wdata[7:0];
                    if (req_wstrb[1]) data_way0[req_index][111:104] <= req_wdata[15:8];
                    if (req_wstrb[2]) data_way0[req_index][119:112] <= req_wdata[23:16];
                    if (req_wstrb[3]) data_way0[req_index][127:120] <= req_wdata[31:24];
                end
            endcase
        end else if (hit_way1) begin
            // 更新Way1的数据
            case (req_offset[3:2])
                2'b00: begin
                    if (req_wstrb[0]) data_way1[req_index][7:0]    <= req_wdata[7:0];
                    if (req_wstrb[1]) data_way1[req_index][15:8]   <= req_wdata[15:8];
                    if (req_wstrb[2]) data_way1[req_index][23:16]  <= req_wdata[23:16];
                    if (req_wstrb[3]) data_way1[req_index][31:24]  <= req_wdata[31:24];
                end
                2'b01: begin
                    if (req_wstrb[0]) data_way1[req_index][39:32]  <= req_wdata[7:0];
                    if (req_wstrb[1]) data_way1[req_index][47:40]  <= req_wdata[15:8];
                    if (req_wstrb[2]) data_way1[req_index][55:48]  <= req_wdata[23:16];
                    if (req_wstrb[3]) data_way1[req_index][63:56]  <= req_wdata[31:24];
                end
                2'b10: begin
                    if (req_wstrb[0]) data_way1[req_index][71:64]  <= req_wdata[7:0];
                    if (req_wstrb[1]) data_way1[req_index][79:72]  <= req_wdata[15:8];
                    if (req_wstrb[2]) data_way1[req_index][87:80]  <= req_wdata[23:16];
                    if (req_wstrb[3]) data_way1[req_index][95:88]  <= req_wdata[31:24];
                end
                2'b11: begin
                    if (req_wstrb[0]) data_way1[req_index][103:96]  <= req_wdata[7:0];
                    if (req_wstrb[1]) data_way1[req_index][111:104] <= req_wdata[15:8];
                    if (req_wstrb[2]) data_way1[req_index][119:112] <= req_wdata[23:16];
                    if (req_wstrb[3]) data_way1[req_index][127:120] <= req_wdata[31:24];
                end
            endcase
        end
    end
end

// LRU更新
always @(posedge clk_g) begin
    if (!resetn) begin
        // 初始化已在initial块中完成
    end else if (state == LOOKUP && cache_hit) begin
        if (hit_way0) begin
            lru[req_index] <= 1'b0;  // 记录Way0是最近使用
        end else if (hit_way1) begin
            lru[req_index] <= 1'b1;  // 记录Way1是最近使用
        end
    end else if (state == REFILL && ret_valid && ret_last) begin
        if (replace_way == 1'b0) begin
            lru[req_index] <= 1'b0;  // Way0刚被使用/填充
        end else begin
            lru[req_index] <= 1'b1;  // Way1刚被使用/填充
        end
    end
end

// AXI读请求 - 在进入REFILL状态时发起（无论是从MISS还是REPLACE）
always @(posedge clk_g) begin
    if (!resetn) begin
        rd_req_r  <= 1'b0;
        rd_type_r <= 3'b0;
        rd_addr_r <= 32'b0;
    end else if ((state == MISS || state == REPLACE) && next_state == REFILL) begin
        rd_req_r  <= 1'b1;
        rd_type_r <= 3'b100;  // Cache行
        rd_addr_r <= {req_tag, req_index, 4'b0};
    end else if (rd_req_r && rd_rdy) begin
        rd_req_r  <= 1'b0;
    end
end

// AXI写请求（替换）
always @(posedge clk_g) begin
    if (!resetn) begin
        wr_req_r   <= 1'b0;
        wr_type_r  <= 3'b0;
        wr_addr_r  <= 32'b0;
        wr_wstrb_r <= 4'b0;
        wr_data_r  <= 128'b0;
    end else if (state == MISS && next_state == REPLACE) begin
        wr_req_r   <= 1'b1;
        wr_type_r  <= 3'b100;  // Cache行
        wr_wstrb_r <= 4'b1111;
        if (replace_way == 1'b0) begin
            wr_addr_r <= {tag_way0[req_index], req_index, 4'b0};
            // 最高8位mask成0xFF（因为写入时最后一个字的wstrb是4'b0111）
            wr_data_r <= {8'hFF, data_way0[req_index][119:0]};
        end else begin
            wr_addr_r <= {tag_way1[req_index], req_index, 4'b0};
            // 最高8位mask成0xFF
            wr_data_r <= {8'hFF, data_way1[req_index][119:0]};
        end
    end else if (wr_req_r && wr_rdy) begin
        wr_req_r  <= 1'b0;
    end
end

// Refill计数器
always @(posedge clk_g) begin
    if (!resetn) begin
        refill_cnt <= 2'b0;
    end else if (state == REFILL && ret_valid) begin
        refill_cnt <= refill_cnt + 1'b1;
    end else if (state != REFILL) begin
        refill_cnt <= 2'b0;
    end
end

// Refill数据写入 - 直接写入data_way
always @(posedge clk_g) begin
    if (state == REFILL && ret_valid) begin
        if (replace_way == 1'b0) begin
            // Refill到Way0
            case (refill_cnt)
                2'b00: data_way0[req_index][31:0]    <= ret_data;
                2'b01: data_way0[req_index][63:32]   <= ret_data;
                2'b10: data_way0[req_index][95:64]   <= ret_data;
                2'b11: data_way0[req_index][127:96]  <= ret_data;
            endcase
            if (ret_last) begin
                tagv_way0[req_index] <= 1'b1;
                tag_way0[req_index]  <= req_tag;
            end
        end else begin
            // Refill到Way1
            case (refill_cnt)
                2'b00: data_way1[req_index][31:0]    <= ret_data;
                2'b01: data_way1[req_index][63:32]   <= ret_data;
                2'b10: data_way1[req_index][95:64]   <= ret_data;
                2'b11: data_way1[req_index][127:96]  <= ret_data;
            endcase
            if (ret_last) begin
                tagv_way1[req_index] <= 1'b1;
                tag_way1[req_index]  <= req_tag;
            end
        end
    end
end

endmodule
