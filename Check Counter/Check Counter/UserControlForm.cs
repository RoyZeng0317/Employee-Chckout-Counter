using System.Windows.Forms;

namespace Check_Counter
{
    public partial class UserControlForm : Form
    {
        public UserControlForm()
        {
            InitializeComponent();
            InitializeGrid();
        }

        private void InitializeGrid()
        {
            dataGridView1.Columns.Clear();
            dataGridView1.Columns.Add("ProductName", "商品名稱");
            dataGridView1.Columns.Add("Quantity",    "數量");
            dataGridView1.Columns.Add("Price",       "單價");
            dataGridView1.Columns.Add("Subtotal",    "小計");
        }

        public void ClearGrid()
        {
            dataGridView1.Rows.Clear();
            lblTotal.Text     = "$0";
            lblGiveMoney.Text = "$0";
        }

        public void AddProductToGrid(string name, string quantity, string price, string subtotal)
        {
            dataGridView1.Rows.Add(name, quantity, price, subtotal);
        }

        public void UpdateTotal(string total)
        {
            lblTotal.Text = "$" + total;
        }
        public void UpdateGive(string give)
        {
            lblGiveMoney.Text = "$" + give;
        }
    }
}
