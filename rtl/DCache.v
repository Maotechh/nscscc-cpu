// Generator : SpinalHDL v1.14.2    git head : 78f29dc66110fc099a777992b6daa2f803ab445e
// Component : DCache
// Git hash  : 8b54019081ec06557709bbaafbf7a87965e11df2

`timescale 1ns/1ps

module DCache (
  input  wire          _zz_when_Cache_l115,
  input  wire          _zz_8,
  input  wire [31:0]   _zz_when_Cache_l121,
  input  wire [31:0]   _zz_9,
  input  wire [3:0]    _zz_10,
  input  wire          _zz_when_Cache_l121_1,
  output reg           _zz_11,
  output wire [31:0]   _zz_12,
  output reg           _zz_13,
  input  wire          _zz_when_Cache_l119,
  input  wire [1:0]    _zz_when_Cache_l111,
  input  wire [31:0]   _zz_14,
  output wire          _zz_15,
  output wire [31:0]   _zz_16,
  input  wire          when_Cache_l128,
  input  wire [31:0]   _zz_17,
  input  wire          when_Cache_l130,
  output wire          _zz_18,
  output reg           _zz_19,
  output wire [31:0]   _zz_20,
  output wire [31:0]   _zz_21,
  input  wire          when_Cache_l127,
  input  wire          clk,
  input  wire          reset
);

  wire       [0:0]    _zz_23_spinal_port0;
  wire       [0:0]    _zz_23_spinal_port1;
  wire       [19:0]   _zz_24_spinal_port0;
  wire       [19:0]   _zz_24_spinal_port1;
  wire       [0:0]    _zz_25_spinal_port2;
  wire       [31:0]   _zz_26_spinal_port0;
  wire       [4:0]    _zz__zz_34;
  wire       [8:0]    _zz__zz_23_port;
  wire       [0:0]    _zz__zz_23_port_1;
  wire       [8:0]    _zz__zz_23_port_2;
  wire       [0:0]    _zz__zz_23_port_3;
  wire       [8:0]    _zz__zz_25_port;
  wire       [0:0]    _zz__zz_25_port_1;
  wire       [8:0]    _zz__zz_25_port_2;
  wire       [0:0]    _zz__zz_25_port_3;
  wire       [8:0]    _zz__zz_23_port_4;
  wire       [0:0]    _zz__zz_23_port_5;
  wire       [8:0]    _zz__zz_24_port;
  wire       [19:0]   _zz__zz_24_port_1;
  wire       [8:0]    _zz__zz_25_port_4;
  wire       [0:0]    _zz__zz_25_port_5;
  reg                 _zz_1;
  reg                 _zz_2;
  reg                 _zz_3;
  reg                 _zz_4;
  reg                 _zz_5;
  reg                 _zz_6;
  reg                 _zz_7;
  wire       [7:0]    _zz_when_Cache_l121_2;
  wire       [19:0]   _zz_when_Cache_l121_3;
  wire       [7:0]    _zz_22;
  reg        [31:0]   _zz_27;
  reg                 when_Cache_l119;
  reg        [1:0]    _zz_when_Cache_l111_1;
  reg                 _zz_when_Cache_l121_4;
  reg        [2:0]    switch_Cache_l114;
  reg        [31:0]   _zz_28;
  reg        [0:0]    _zz_switch_Cache_l114;
  reg        [1:0]    _zz_29;
  reg        [7:0]    _zz_switch_Cache_l114_1;
  wire       [8:0]    _zz_when_Cache_l121_5;
  wire       [8:0]    _zz_when_Cache_l121_6;
  wire       [8:0]    _zz_when_Cache_l121_7;
  wire       [8:0]    _zz_when_Cache_l121_8;
  wire                when_Cache_l121;
  wire       [10:0]   _zz_34;
  wire                when_Cache_l111;
  wire                when_Cache_l115;
  wire       [8:0]    _zz_switch_Cache_l114_2;
  (* ram_style = "distributed" *) reg [0:0] _zz_23 [0:511];
  (* ram_style = "distributed" *) reg [19:0] _zz_24 [0:511];
  (* ram_style = "distributed" *) reg [0:0] _zz_25 [0:511];
  reg [31:0] _zz_26 [0:2047];

  assign _zz__zz_34 = {{_zz_switch_Cache_l114,_zz_29},_zz_27[3 : 2]};
  assign _zz__zz_23_port = {_zz_22,1'b0};
  assign _zz__zz_23_port_1 = 1'b0;
  assign _zz__zz_23_port_2 = {_zz_22,1'b1};
  assign _zz__zz_23_port_3 = 1'b0;
  assign _zz__zz_23_port_4 = {_zz_switch_Cache_l114_1,_zz_switch_Cache_l114};
  assign _zz__zz_23_port_5 = 1'b1;
  assign _zz__zz_24_port = {_zz_switch_Cache_l114_1,_zz_switch_Cache_l114};
  assign _zz__zz_24_port_1 = _zz_27[31 : 12];
  assign _zz__zz_25_port = {_zz_22,1'b0};
  assign _zz__zz_25_port_1 = 1'b0;
  assign _zz__zz_25_port_2 = {_zz_22,1'b1};
  assign _zz__zz_25_port_3 = 1'b0;
  assign _zz__zz_25_port_4 = {_zz_switch_Cache_l114_1,_zz_switch_Cache_l114};
  assign _zz__zz_25_port_5 = 1'b0;
  assign _zz_23_spinal_port0 = _zz_23[_zz_when_Cache_l121_5];
  assign _zz_23_spinal_port1 = _zz_23[_zz_when_Cache_l121_7];
  always @(posedge clk) begin
    if(_zz_7) begin
      _zz_23[_zz__zz_23_port] <= _zz__zz_23_port_1;
    end
  end

  always @(posedge clk) begin
    if(_zz_6) begin
      _zz_23[_zz__zz_23_port_2] <= _zz__zz_23_port_3;
    end
  end

  always @(posedge clk) begin
    if(_zz_3) begin
      _zz_23[_zz__zz_23_port_4] <= _zz__zz_23_port_5;
    end
  end

  assign _zz_24_spinal_port0 = _zz_24[_zz_when_Cache_l121_6];
  assign _zz_24_spinal_port1 = _zz_24[_zz_when_Cache_l121_8];
  always @(posedge clk) begin
    if(_zz_2) begin
      _zz_24[_zz__zz_24_port] <= _zz__zz_24_port_1;
    end
  end

  always @(posedge clk) begin
    if(_zz_5) begin
      _zz_25[_zz__zz_25_port] <= _zz__zz_25_port_1;
    end
  end

  always @(posedge clk) begin
    if(_zz_4) begin
      _zz_25[_zz__zz_25_port_2] <= _zz__zz_25_port_3;
    end
  end

  assign _zz_25_spinal_port2 = _zz_25[_zz_switch_Cache_l114_2];
  always @(posedge clk) begin
    if(_zz_1) begin
      _zz_25[_zz__zz_25_port_4] <= _zz__zz_25_port_5;
    end
  end

  assign _zz_26_spinal_port0 = _zz_26[_zz_34];
  always @(*) begin
    _zz_1 = 1'b0;
    case(switch_Cache_l114)
      3'b011 : begin
        if(when_Cache_l128) begin
          if(when_Cache_l130) begin
            _zz_1 = 1'b1;
          end
        end
      end
      default : begin
      end
    endcase
  end

  always @(*) begin
    _zz_2 = 1'b0;
    case(switch_Cache_l114)
      3'b011 : begin
        if(when_Cache_l128) begin
          if(when_Cache_l130) begin
            _zz_2 = 1'b1;
          end
        end
      end
      default : begin
      end
    endcase
  end

  always @(*) begin
    _zz_3 = 1'b0;
    case(switch_Cache_l114)
      3'b011 : begin
        if(when_Cache_l128) begin
          if(when_Cache_l130) begin
            _zz_3 = 1'b1;
          end
        end
      end
      default : begin
      end
    endcase
  end

  always @(*) begin
    _zz_4 = 1'b0;
    if(when_Cache_l111) begin
      _zz_4 = 1'b1;
    end
  end

  always @(*) begin
    _zz_5 = 1'b0;
    if(when_Cache_l111) begin
      _zz_5 = 1'b1;
    end
  end

  always @(*) begin
    _zz_6 = 1'b0;
    if(when_Cache_l111) begin
      _zz_6 = 1'b1;
    end
  end

  always @(*) begin
    _zz_7 = 1'b0;
    if(when_Cache_l111) begin
      _zz_7 = 1'b1;
    end
  end

  assign _zz_when_Cache_l121_2 = _zz_when_Cache_l121[11 : 4];
  assign _zz_when_Cache_l121_3 = _zz_when_Cache_l121[31 : 12];
  assign _zz_22 = _zz_14[11 : 4];
  assign _zz_when_Cache_l121_5 = {_zz_when_Cache_l121_2,1'b0};
  assign _zz_when_Cache_l121_6 = {_zz_when_Cache_l121_2,1'b0};
  assign _zz_when_Cache_l121_7 = {_zz_when_Cache_l121_2,1'b1};
  assign _zz_when_Cache_l121_8 = {_zz_when_Cache_l121_2,1'b1};
  assign when_Cache_l121 = ((((_zz_23_spinal_port0[0] && (_zz_24_spinal_port0 == _zz_when_Cache_l121_3)) || (_zz_23_spinal_port1[0] && (_zz_24_spinal_port1 == _zz_when_Cache_l121_3))) && (! _zz_when_Cache_l121_4)) || when_Cache_l119);
  always @(*) begin
    _zz_13 = 1'b0;
    case(switch_Cache_l114)
      3'b001 : begin
        if(!when_Cache_l119) begin
          if(!when_Cache_l121) begin
            _zz_13 = 1'b1;
          end
        end
      end
      default : begin
      end
    endcase
  end

  always @(*) begin
    _zz_11 = 1'b0;
    case(switch_Cache_l114)
      3'b001 : begin
        if(when_Cache_l119) begin
          _zz_11 = 1'b1;
        end else begin
          if(when_Cache_l121) begin
            _zz_11 = 1'b1;
          end
        end
      end
      3'b011 : begin
        if(when_Cache_l128) begin
          if(when_Cache_l130) begin
            _zz_11 = 1'b1;
          end
        end
      end
      default : begin
      end
    endcase
  end

  assign _zz_15 = 1'b0;
  assign _zz_16 = _zz_28;
  assign _zz_18 = 1'b1;
  always @(*) begin
    _zz_19 = 1'b0;
    case(switch_Cache_l114)
      3'b010 : begin
        _zz_19 = 1'b1;
      end
      default : begin
      end
    endcase
  end

  assign _zz_20 = 32'h0;
  assign _zz_21 = 32'h0;
  assign _zz_34 = {6'd0, _zz__zz_34};
  assign _zz_12 = _zz_26_spinal_port0;
  assign when_Cache_l111 = (when_Cache_l119 && (when_Cache_l119 && (_zz_when_Cache_l111_1 == 2'b00)));
  assign when_Cache_l115 = (_zz_when_Cache_l115 || _zz_when_Cache_l119);
  assign _zz_switch_Cache_l114_2 = {_zz_switch_Cache_l114_1,_zz_switch_Cache_l114};
  always @(posedge clk or posedge reset) begin
    if(reset) begin
      switch_Cache_l114 <= 3'b000;
    end else begin
      case(switch_Cache_l114)
        3'b000 : begin
          if(when_Cache_l115) begin
            switch_Cache_l114 <= 3'b001;
          end
        end
        3'b001 : begin
          if(when_Cache_l119) begin
            switch_Cache_l114 <= 3'b000;
          end else begin
            if(when_Cache_l121) begin
              switch_Cache_l114 <= 3'b000;
            end else begin
              switch_Cache_l114 <= (_zz_25_spinal_port2[0] ? 3'b010 : 3'b011);
            end
          end
        end
        3'b010 : begin
          if(when_Cache_l127) begin
            switch_Cache_l114 <= 3'b011;
          end
        end
        3'b011 : begin
          if(when_Cache_l128) begin
            if(when_Cache_l130) begin
              switch_Cache_l114 <= 3'b000;
            end
          end
        end
        default : begin
        end
      endcase
    end
  end

  always @(posedge clk) begin
    case(switch_Cache_l114)
      3'b000 : begin
        if(when_Cache_l115) begin
          _zz_27 <= (_zz_when_Cache_l119 ? _zz_14 : _zz_when_Cache_l121);
          when_Cache_l119 <= _zz_when_Cache_l119;
          _zz_when_Cache_l111_1 <= _zz_when_Cache_l111;
          _zz_when_Cache_l121_4 <= _zz_when_Cache_l121_1;
        end
      end
      3'b001 : begin
        if(when_Cache_l119) begin
          when_Cache_l119 <= 1'b0;
        end else begin
          if(!when_Cache_l121) begin
            _zz_28 <= _zz_27;
            _zz_switch_Cache_l114 <= (_zz_switch_Cache_l114 + 1'b1);
            _zz_29 <= 2'b00;
            _zz_switch_Cache_l114_1 <= _zz_when_Cache_l121_2;
          end
        end
      end
      3'b011 : begin
        if(when_Cache_l128) begin
          _zz_29 <= (_zz_29 + 2'b01);
        end
      end
      default : begin
      end
    endcase
  end


endmodule
