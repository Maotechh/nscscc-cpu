// Generator : SpinalHDL v1.14.2    git head : 78f29dc66110fc099a777992b6daa2f803ab445e
// Component : mul



module mul (
  input  wire          mul_clk,
  input  wire          reset,
  input  wire          mul_signed,
  input  wire [31:0]   x,
  input  wire [31:0]   y,
  output wire [63:0]   result
);

  wire       [63:0]   _zz_unsignedProduct;
  wire       [63:0]   _zz_signedProduct;
  wire       [31:0]   _zz_signedProduct_1;
  wire       [31:0]   _zz_signedProduct_2;
  wire       [63:0]   unsignedProduct;
  wire       [63:0]   signedProduct;
  wire       [63:0]   selectedProduct;
  reg        [63:0]   capture_product;
  wire                when_OpenLa500Mul_l36;

  assign _zz_unsignedProduct = (x * y);
  assign _zz_signedProduct = ($signed(_zz_signedProduct_1) * $signed(_zz_signedProduct_2));
  assign _zz_signedProduct_1 = x;
  assign _zz_signedProduct_2 = y;
  assign unsignedProduct = _zz_unsignedProduct;
  assign signedProduct = _zz_signedProduct;
  assign selectedProduct = (mul_signed ? signedProduct : unsignedProduct);
  assign when_OpenLa500Mul_l36 = (! reset);
  assign result = capture_product;
  always @(posedge mul_clk) begin
    if(when_OpenLa500Mul_l36) begin
      capture_product <= selectedProduct;
    end
  end


endmodule
