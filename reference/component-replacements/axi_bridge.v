// Generator : SpinalHDL v1.14.2    git head : 78f29dc66110fc099a777992b6daa2f803ab445e
// Component : axi_bridge



module axi_bridge (
  input  wire          clk,
  input  wire          reset,
  output wire [3:0]    arid,
  output wire [31:0]   araddr,
  output wire [7:0]    arlen,
  output wire [2:0]    arsize,
  output wire [1:0]    arburst,
  output wire [1:0]    arlock,
  output wire [3:0]    arcache,
  output wire [2:0]    arprot,
  output wire          arvalid,
  input  wire          arready,
  input  wire [3:0]    rid,
  input  wire [31:0]   rdata,
  input  wire [1:0]    rresp,
  input  wire          rlast,
  input  wire          rvalid,
  output wire          rready,
  output wire [3:0]    awid,
  output wire [31:0]   awaddr,
  output wire [7:0]    awlen,
  output wire [2:0]    awsize,
  output wire [1:0]    awburst,
  output wire [1:0]    awlock,
  output wire [3:0]    awcache,
  output wire [2:0]    awprot,
  output wire          awvalid,
  input  wire          awready,
  output wire [3:0]    wid,
  output wire [31:0]   wdata,
  output wire [3:0]    wstrb,
  output wire          wlast,
  output wire          wvalid,
  input  wire          wready,
  input  wire [3:0]    bid,
  input  wire [1:0]    bresp,
  input  wire          bvalid,
  output wire          bready,
  input  wire          inst_rd_req,
  input  wire [2:0]    inst_rd_type,
  input  wire [31:0]   inst_rd_addr,
  output wire          inst_rd_rdy,
  output wire          inst_ret_valid,
  output wire          inst_ret_last,
  output wire [31:0]   inst_ret_data,
  input  wire          inst_wr_req,
  input  wire [2:0]    inst_wr_type,
  input  wire [31:0]   inst_wr_addr,
  input  wire [3:0]    inst_wr_wstrb,
  input  wire [127:0]  inst_wr_data,
  output wire          inst_wr_rdy,
  input  wire          data_rd_req,
  input  wire [2:0]    data_rd_type,
  input  wire [31:0]   data_rd_addr,
  output wire          data_rd_rdy,
  output wire          data_ret_valid,
  output wire          data_ret_last,
  output wire [31:0]   data_ret_data,
  input  wire          data_wr_req,
  input  wire [2:0]    data_wr_type,
  input  wire [31:0]   data_wr_addr,
  input  wire [3:0]    data_wr_wstrb,
  input  wire [127:0]  data_wr_data,
  output wire          data_wr_rdy,
  output wire          write_buffer_empty
);

  wire       [2:0]    logic_WriteEmpty;
  wire       [2:0]    logic_WriteDataTransform;
  wire       [2:0]    logic_WriteDataWait;
  wire       [2:0]    logic_WriteWaitResponse;
  reg                 logic_readRequestBusy;
  reg                 logic_readResponseBusy;
  reg        [2:0]    logic_writeState;
  reg        [3:0]    logic_arid;
  reg        [31:0]   logic_araddr;
  reg        [7:0]    logic_arlen;
  reg        [2:0]    logic_arsize;
  reg                 logic_arvalid;
  reg                 logic_rready;
  reg        [31:0]   logic_awaddr;
  reg        [7:0]    logic_awlen;
  reg        [2:0]    logic_awsize;
  reg                 logic_awvalid;
  reg        [31:0]   logic_wdata;
  reg        [3:0]    logic_wstrb;
  reg                 logic_wlast;
  reg                 logic_wvalid;
  reg                 logic_bready;
  reg        [127:0]  logic_writeBufferData;
  reg        [2:0]    logic_writeBufferCount;
  wire                logic_writeBusy;
  wire                logic_completingWrite;
  wire                when_OpenLa500AxiBridge_l149;
  wire                when_OpenLa500AxiBridge_l151;
  wire                _zz_logic_arlen;
  wire                when_OpenLa500AxiBridge_l155;
  wire                _zz_logic_arlen_1;
  wire                when_OpenLa500AxiBridge_l164;
  wire                when_OpenLa500AxiBridge_l165;
  wire                when_OpenLa500AxiBridge_l169;
  wire                when_OpenLa500AxiBridge_l186;
  wire                when_OpenLa500AxiBridge_l209;
  wire                when_OpenLa500AxiBridge_l220;
  wire                readCanReceive;

  assign logic_WriteEmpty = 3'b000;
  assign logic_WriteDataTransform = 3'b100;
  assign logic_WriteDataWait = 3'b101;
  assign logic_WriteWaitResponse = 3'b110;
  assign logic_writeBusy = (logic_writeState != logic_WriteEmpty);
  assign logic_completingWrite = (bvalid && logic_bready);
  assign when_OpenLa500AxiBridge_l149 = (! logic_readRequestBusy);
  assign when_OpenLa500AxiBridge_l151 = ((! logic_writeBusy) || logic_completingWrite);
  assign _zz_logic_arlen = (data_rd_type == 3'b100);
  assign when_OpenLa500AxiBridge_l155 = ((! logic_writeBusy) || logic_completingWrite);
  assign _zz_logic_arlen_1 = (inst_rd_type == 3'b100);
  assign when_OpenLa500AxiBridge_l164 = (! logic_readResponseBusy);
  assign when_OpenLa500AxiBridge_l165 = (rvalid && logic_rready);
  assign when_OpenLa500AxiBridge_l169 = (rlast && rvalid);
  assign when_OpenLa500AxiBridge_l186 = (data_wr_type == 3'b100);
  assign when_OpenLa500AxiBridge_l209 = (logic_writeBufferCount == 3'b001);
  assign when_OpenLa500AxiBridge_l220 = (bvalid && logic_bready);
  assign readCanReceive = ((! logic_readRequestBusy) && (! (logic_writeBusy && (! (bvalid && logic_bready)))));
  assign arid = logic_arid;
  assign araddr = logic_araddr;
  assign arlen = logic_arlen;
  assign arsize = logic_arsize;
  assign arburst = 2'b01;
  assign arlock = 2'b00;
  assign arcache = 4'b0000;
  assign arprot = 3'b000;
  assign arvalid = logic_arvalid;
  assign rready = logic_rready;
  assign awid = 4'b0001;
  assign awaddr = logic_awaddr;
  assign awlen = logic_awlen;
  assign awsize = logic_awsize;
  assign awburst = 2'b01;
  assign awlock = 2'b00;
  assign awcache = 4'b0000;
  assign awprot = 3'b000;
  assign awvalid = logic_awvalid;
  assign wid = 4'b0001;
  assign wdata = logic_wdata;
  assign wstrb = logic_wstrb;
  assign wlast = logic_wlast;
  assign wvalid = logic_wvalid;
  assign bready = logic_bready;
  assign inst_rd_rdy = ((! data_rd_req) && readCanReceive);
  assign inst_ret_valid = ((! rid[0]) && rvalid);
  assign inst_ret_last = ((! rid[0]) && rlast);
  assign inst_ret_data = rdata;
  assign inst_wr_rdy = 1'b1;
  assign data_rd_rdy = readCanReceive;
  assign data_ret_valid = (rid[0] && rvalid);
  assign data_ret_last = (rid[0] && rlast);
  assign data_ret_data = rdata;
  assign data_wr_rdy = (! logic_writeBusy);
  assign write_buffer_empty = ((logic_writeBufferCount == 3'b000) && (! logic_writeBusy));
  always @(posedge clk) begin
    if(reset) begin
      logic_readRequestBusy <= 1'b0;
      logic_readResponseBusy <= 1'b0;
      logic_writeState <= logic_WriteEmpty;
      logic_arvalid <= 1'b0;
      logic_rready <= 1'b1;
      logic_awvalid <= 1'b0;
      logic_wlast <= 1'b0;
      logic_wvalid <= 1'b0;
      logic_bready <= 1'b0;
      logic_writeBufferData <= 128'h0;
      logic_writeBufferCount <= 3'b000;
    end else begin
      logic_rready <= logic_rready;
      if(when_OpenLa500AxiBridge_l149) begin
        if(data_rd_req) begin
          if(when_OpenLa500AxiBridge_l151) begin
            logic_readRequestBusy <= 1'b1;
            logic_arvalid <= 1'b1;
          end
        end else begin
          if(inst_rd_req) begin
            if(when_OpenLa500AxiBridge_l155) begin
              logic_readRequestBusy <= 1'b1;
              logic_arvalid <= 1'b1;
            end
          end
        end
      end else begin
        if(arready) begin
          logic_readRequestBusy <= 1'b0;
          logic_arvalid <= 1'b0;
        end
      end
      if(when_OpenLa500AxiBridge_l164) begin
        if(when_OpenLa500AxiBridge_l165) begin
          logic_readResponseBusy <= 1'b1;
        end
      end else begin
        if(when_OpenLa500AxiBridge_l169) begin
          logic_readResponseBusy <= 1'b0;
        end
      end
      if((logic_writeState == logic_WriteEmpty)) begin
          if(data_wr_req) begin
            logic_writeState <= logic_WriteDataWait;
            logic_awvalid <= 1'b1;
            logic_writeBufferData <= {32'h0,data_wr_data[127 : 32]};
            if(when_OpenLa500AxiBridge_l186) begin
              logic_writeBufferCount <= 3'b011;
            end else begin
              logic_writeBufferCount <= 3'b000;
              logic_wlast <= 1'b1;
            end
          end
      end else if((logic_writeState == logic_WriteDataWait)) begin
          if(awready) begin
            logic_writeState <= logic_WriteDataTransform;
            logic_awvalid <= 1'b0;
            logic_wvalid <= 1'b1;
          end
      end else if((logic_writeState == logic_WriteDataTransform)) begin
          if(wready) begin
            if(logic_wlast) begin
              logic_writeState <= logic_WriteWaitResponse;
              logic_wvalid <= 1'b0;
              logic_wlast <= 1'b0;
              logic_bready <= 1'b1;
            end else begin
              if(when_OpenLa500AxiBridge_l209) begin
                logic_wlast <= 1'b1;
              end
              logic_wvalid <= 1'b1;
              logic_writeBufferData <= {32'h0,logic_writeBufferData[127 : 32]};
              logic_writeBufferCount <= (logic_writeBufferCount - 3'b001);
            end
          end
      end else if((logic_writeState == logic_WriteWaitResponse)) begin
          if(when_OpenLa500AxiBridge_l220) begin
            logic_writeState <= logic_WriteEmpty;
            logic_bready <= 1'b0;
          end
      end else begin
          logic_writeState <= logic_WriteEmpty;
      end
    end
  end

  always @(posedge clk) begin
    if(when_OpenLa500AxiBridge_l149) begin
      if(data_rd_req) begin
        if(when_OpenLa500AxiBridge_l151) begin
          logic_arid <= 4'b0001;
          logic_araddr <= data_rd_addr;
          logic_arsize <= (_zz_logic_arlen ? 3'b010 : data_rd_type);
          logic_arlen <= (_zz_logic_arlen ? 8'h03 : 8'h0);
        end
      end else begin
        if(inst_rd_req) begin
          if(when_OpenLa500AxiBridge_l155) begin
            logic_arid <= 4'b0000;
            logic_araddr <= inst_rd_addr;
            logic_arsize <= (_zz_logic_arlen_1 ? 3'b010 : inst_rd_type);
            logic_arlen <= (_zz_logic_arlen_1 ? 8'h03 : 8'h0);
          end
        end
      end
    end
    if((logic_writeState == logic_WriteEmpty)) begin
        if(data_wr_req) begin
          logic_awaddr <= data_wr_addr;
          logic_awsize <= (when_OpenLa500AxiBridge_l186 ? 3'b010 : data_wr_type);
          logic_awlen <= (when_OpenLa500AxiBridge_l186 ? 8'h03 : 8'h0);
          logic_wdata <= data_wr_data[31 : 0];
          logic_wstrb <= data_wr_wstrb;
        end
    end else if((logic_writeState == logic_WriteDataWait)) begin
    end else if((logic_writeState == logic_WriteDataTransform)) begin
        if(wready) begin
          if(!logic_wlast) begin
            logic_wdata <= logic_writeBufferData[31 : 0];
          end
        end
    end else if((logic_writeState == logic_WriteWaitResponse)) begin
    end else begin
    end
  end


endmodule
