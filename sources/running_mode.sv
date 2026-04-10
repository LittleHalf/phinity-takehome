`timescale 1us/1us

// Golden: running mode — Icarus-friendly (no variable array select in sensitive always_* issues).

module running_mode (
  input  logic        clk,
  input  logic        rst,
  input  logic        valid,
  input  logic        change_only,
  input  logic [6:0]  data_in,
  output logic [6:0]  mode_out
);

  logic [15:0] count [0:127];
  logic [15:0] count_incr [0:127];
  logic [6:0]  old_winner;
  logic [6:0]  new_winner;

  integer j;

  initial begin
    mode_out = 7'd0;
    for (j = 0; j < 128; j = j + 1)
      count[j] = 16'd0;
  end

  integer unsigned max_c_pre;
  integer unsigned max_c_post;
  reg found_o;
  reg found_n;

  always @(*) begin
    for (j = 0; j < 128; j = j + 1)
      count_incr[j] = count[j];
    if (valid)
      count_incr[data_in] = count[data_in] + 16'd1;
  end

  always @(*) begin
    max_c_pre = 0;
    for (j = 0; j < 128; j = j + 1) begin
      if (count[j] > max_c_pre)
        max_c_pre = count[j];
    end
    old_winner = 7'd0;
    found_o = 1'b0;
    for (j = 0; j < 128; j = j + 1) begin
      if (!found_o && (count[j] == max_c_pre)) begin
        old_winner = j[6:0];
        found_o = 1'b1;
      end
    end
  end

  always @(*) begin
    max_c_post = 0;
    for (j = 0; j < 128; j = j + 1) begin
      if (count_incr[j] > max_c_post)
        max_c_post = count_incr[j];
    end
    new_winner = 7'd0;
    found_n = 1'b0;
    for (j = 0; j < 128; j = j + 1) begin
      if (!found_n && (count_incr[j] == max_c_post)) begin
        new_winner = j[6:0];
        found_n = 1'b1;
      end
    end
  end

  always_ff @(posedge clk) begin
    if (rst) begin
      for (j = 0; j < 128; j = j + 1)
        count[j] <= 16'd0;
      mode_out <= 7'd0;
    end else if (valid) begin
      count[data_in] <= count[data_in] + 16'd1;
      if (change_only) begin
        if (new_winner != old_winner)
          mode_out <= new_winner;
        else
          mode_out <= 7'd0;
      end else begin
        mode_out <= new_winner;
      end
    end
  end

endmodule
