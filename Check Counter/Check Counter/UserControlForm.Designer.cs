namespace Check_Counter
{
    partial class UserControlForm
    {
        private System.ComponentModel.IContainer components = null;

        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
                components.Dispose();
            base.Dispose(disposing);
        }

        private void InitializeComponent()
        {
            this.lblTitle = new System.Windows.Forms.Label();
            this.dataGridView1 = new System.Windows.Forms.DataGridView();
            this.lblTotalLabel = new System.Windows.Forms.Label();
            this.lblTotal = new System.Windows.Forms.Label();
            this.lblGive = new System.Windows.Forms.Label();
            this.lblGiveMoney = new System.Windows.Forms.Label();
            ((System.ComponentModel.ISupportInitialize)(this.dataGridView1)).BeginInit();
            this.SuspendLayout();
            // 
            // lblTitle
            // 
            this.lblTitle.BackColor = System.Drawing.Color.SteelBlue;
            this.lblTitle.Dock = System.Windows.Forms.DockStyle.Top;
            this.lblTitle.Font = new System.Drawing.Font("標楷體", 28F, System.Drawing.FontStyle.Bold);
            this.lblTitle.ForeColor = System.Drawing.Color.White;
            this.lblTitle.Location = new System.Drawing.Point(0, 0);
            this.lblTitle.Name = "lblTitle";
            this.lblTitle.Size = new System.Drawing.Size(1024, 80);
            this.lblTitle.TabIndex = 0;
            this.lblTitle.Text = "歡迎光臨";
            this.lblTitle.TextAlign = System.Drawing.ContentAlignment.MiddleCenter;
            // 
            // dataGridView1
            // 
            this.dataGridView1.AllowUserToAddRows = false;
            this.dataGridView1.AllowUserToDeleteRows = false;
            this.dataGridView1.AutoSizeColumnsMode = System.Windows.Forms.DataGridViewAutoSizeColumnsMode.Fill;
            this.dataGridView1.ColumnHeadersHeightSizeMode = System.Windows.Forms.DataGridViewColumnHeadersHeightSizeMode.AutoSize;
            this.dataGridView1.Font = new System.Drawing.Font("標楷體", 14F);
            this.dataGridView1.Location = new System.Drawing.Point(0, 80);
            this.dataGridView1.Name = "dataGridView1";
            this.dataGridView1.ReadOnly = true;
            this.dataGridView1.RowTemplate.Height = 40;
            this.dataGridView1.Size = new System.Drawing.Size(1024, 580);
            this.dataGridView1.TabIndex = 0;
            // 
            // lblTotalLabel
            // 
            this.lblTotalLabel.Font = new System.Drawing.Font("標楷體", 20F);
            this.lblTotalLabel.Location = new System.Drawing.Point(237, 687);
            this.lblTotalLabel.Name = "lblTotalLabel";
            this.lblTotalLabel.Size = new System.Drawing.Size(138, 50);
            this.lblTotalLabel.TabIndex = 1;
            this.lblTotalLabel.Text = "應付金額:";
            this.lblTotalLabel.TextAlign = System.Drawing.ContentAlignment.MiddleRight;
            // 
            // lblTotal
            // 
            this.lblTotal.Font = new System.Drawing.Font("標楷體", 28F, System.Drawing.FontStyle.Bold);
            this.lblTotal.ForeColor = System.Drawing.Color.DarkRed;
            this.lblTotal.Location = new System.Drawing.Point(381, 687);
            this.lblTotal.Name = "lblTotal";
            this.lblTotal.Size = new System.Drawing.Size(91, 60);
            this.lblTotal.TabIndex = 2;
            this.lblTotal.Text = "$0";
            this.lblTotal.TextAlign = System.Drawing.ContentAlignment.MiddleLeft;
            // 
            // lblGive
            // 
            this.lblGive.Font = new System.Drawing.Font("標楷體", 20F);
            this.lblGive.Location = new System.Drawing.Point(591, 685);
            this.lblGive.Name = "lblGive";
            this.lblGive.Size = new System.Drawing.Size(86, 50);
            this.lblGive.TabIndex = 3;
            this.lblGive.Text = "找零:";
            this.lblGive.TextAlign = System.Drawing.ContentAlignment.MiddleRight;
            // 
            // lblGiveMoney
            // 
            this.lblGiveMoney.Font = new System.Drawing.Font("標楷體", 28F, System.Drawing.FontStyle.Bold);
            this.lblGiveMoney.ForeColor = System.Drawing.Color.DarkRed;
            this.lblGiveMoney.Location = new System.Drawing.Point(683, 679);
            this.lblGiveMoney.Name = "lblGiveMoney";
            this.lblGiveMoney.Size = new System.Drawing.Size(91, 60);
            this.lblGiveMoney.TabIndex = 4;
            this.lblGiveMoney.Text = "$0";
            this.lblGiveMoney.TextAlign = System.Drawing.ContentAlignment.MiddleLeft;
            // 
            // UserControlForm
            // 
            this.AutoScaleDimensions = new System.Drawing.SizeF(6F, 12F);
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.BackColor = System.Drawing.Color.WhiteSmoke;
            this.ClientSize = new System.Drawing.Size(1024, 768);
            this.Controls.Add(this.lblGiveMoney);
            this.Controls.Add(this.lblGive);
            this.Controls.Add(this.lblTitle);
            this.Controls.Add(this.dataGridView1);
            this.Controls.Add(this.lblTotalLabel);
            this.Controls.Add(this.lblTotal);
            this.FormBorderStyle = System.Windows.Forms.FormBorderStyle.FixedSingle;
            this.MaximizeBox = false;
            this.Name = "UserControlForm";
            this.StartPosition = System.Windows.Forms.FormStartPosition.Manual;
            this.Text = "客戶顯示畫面";
            ((System.ComponentModel.ISupportInitialize)(this.dataGridView1)).EndInit();
            this.ResumeLayout(false);

        }

        private System.Windows.Forms.Label lblTitle;
        private System.Windows.Forms.DataGridView dataGridView1;
        private System.Windows.Forms.Label lblTotalLabel;
        private System.Windows.Forms.Label lblTotal;
        private System.Windows.Forms.Label lblGive;
        private System.Windows.Forms.Label lblGiveMoney;
    }
}
