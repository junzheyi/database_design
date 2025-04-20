# database_design
华中科技大学电信学院 大三下学期数据库课程设计 前后端代码

#### 🎯 前端功能说明

进入商品库存管理系统主界面

![image-20250420231750150](https://cdn.jsdelivr.net/gh/junzheyi/typorabed@master/img/image-20250420231750150.png)

在主界面上方有选择表和功能两个选项

![image-20250420231814452](C:\Users\86183\AppData\Roaming\Typora\typora-user-images\image-20250420231814452.png)

![image-20250420231828432](C:\Users\86183\AppData\Roaming\Typora\typora-user-images\image-20250420231828432.png)

以销售记录表为例，可以对记录进行编辑、删除，插入新数据以及关键字搜索

![image-20250420230711330](https://cdn.jsdelivr.net/gh/junzheyi/typorabed@master/img/image-20250420230711330.png)

![image-20250420230803992](C:\Users\86183\AppData\Roaming\Typora\typora-user-images\image-20250420230803992.png)

以计算一段时间内销售利润为例

![image-20250420230920132](https://cdn.jsdelivr.net/gh/junzheyi/typorabed@master/img/image-20250420230920132.png)

**并发性验证：**打开两个浏览器窗口或标签页 两个窗口都访问同一记录的编辑页面 在第一个窗口点击"验证并发"按钮，这将启动一个事务，获取行锁并保持20秒 立即在第二个窗口点击"保存"按钮 会发现第二个窗口的请求会等待，直到第一个窗口的事务完成 （和服务器通信存在部分延迟，但不影响并发效果验证）

![image-20250420230939080](https://cdn.jsdelivr.net/gh/junzheyi/typorabed@master/img/image-20250420230939080.png)

注：此功能的制作目的是方便验收的时候可视化上锁过程

![image-20250420231539098](https://cdn.jsdelivr.net/gh/junzheyi/typorabed@master/img/image-20250420231539098.png)

在服务器后端最后四条记录可以看到两个用户抢占修改数据时的上锁过程，具体代码逻辑参考`app.py`
