`timescale 1us/1us

// Baseline: incomplete — implement frequency tracking, tie-break, and change_only.

module running_mode (
  input  logic        clk,
  input  logic        rst,
  input  logic        valid,
  input  logic        change_only,
  input  logic [6:0]  data_in,
  output logic [6:0]  mode_out
);

  always_ff @(posedge clk) begin
    if (rst) begin
      mode_out <= 7'd0;
    end else if (valid) begin
      mode_out <= data_in;
    end
  end

endmodule
