import torch 
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import pandas as pd
from IPython.display import clear_output
from PINN.generators import generator_2dspatial_segment
from PINN.function import calculate_sigma_rr,calculate_tau_zr

class Monitor2DSpatial:
    r"""A Monitor for 2D steady-state problems
    """
    def __init__(self, check_on_x, check_on_y, check_every,device,args):
        self.using_non_gui_backend = matplotlib.get_backend() == 'agg'
        self.device=device
        xy_tensor = torch.cartesian_prod(check_on_x, check_on_y).to(self.device)
        
        self.xx_tensor = torch.squeeze(xy_tensor[:, 0]).requires_grad_()
        self.yy_tensor = torch.squeeze(xy_tensor[:, 1]).requires_grad_()

        self.xx_array = self.xx_tensor.clone().detach().cpu().numpy()
        self.yy_array = self.yy_tensor.clone().detach().cpu().numpy()

        self.check_every = check_every

        self.check_on_x=check_on_x
        self.check_on_y=check_on_y
        self.args=args

    def check(self, approximator, history,epoch):
        
        torch.save(approximator.single_network,str(self.args.save_dict)+"-model/"+str(epoch)+'.pth')
        clear_output(wait=True)
        fig, axs = plt.subplots(5, 3, figsize=(14, 17))

        #print(self.yy_tensor)

        uu_array = approximator(self.xx_tensor, self.yy_tensor)
        uu_array = torch.nan_to_num(uu_array, nan=0)
        
        sigma_zr=calculate_tau_zr(uu_array[:,0],uu_array[:,1],self.xx_tensor,self.yy_tensor)

        uu_array=uu_array.detach().cpu().numpy()
        sigma_zr=torch.nan_to_num(sigma_zr,nan=0)
        sigma_zr=sigma_zr.detach().cpu().numpy()
        

        np.savetxt(self.args.save_dict + '-uu_array.txt', uu_array)
        
        max_length = max(len(value) for value in history.values())

        # 将字典中的值转换为相同长度的数组
        history_array = np.array([value  for value in history.values()]).T

        np.savetxt(self.args.save_dict + '-history.txt', history_array)

        #sigma_zr=sigma_zr.detach().cpu().numpy()

        xx, yy = np.meshgrid(self.check_on_x, self.check_on_y)
        # 创建热力图
        heatmap=axs[0,0].pcolormesh(xx, yy, uu_array[:,0].reshape(xx.shape).T,cmap='rainbow')  # cmap是颜色映射，你可以根据需要选择
        contour_lines = axs[0,0].contour(xx, yy, uu_array[:,0].reshape(xx.shape).T, 10,colors='black', linewidths=0.5)
        # 添加颜色条
        cbar=plt.colorbar(heatmap,ax=axs[0,0])

        
        num_ticks = 10  # 指定刻度的数量
        tick_values = np.linspace(uu_array[:,0].min(), uu_array[:,0].max(), num_ticks)
        tick_labels = [f'{val:.5f}' for val in tick_values]

        # 设置颜色条的刻度值和标签
        cbar.set_ticks(tick_values)
        cbar.set_ticklabels(tick_labels)

        # 添加轴标签
        axs[0,0].set_xlabel('r')
        axs[0,0].set_ylabel('z')
        axs[0,0].set_title('u')

        heatmap=axs[0,1].pcolormesh(xx, yy, uu_array[:,1].reshape(xx.shape).T,cmap='rainbow')  # cmap是颜色映射，你可以根据需要选择
        contour_lines = axs[0,1].contour(xx, yy, uu_array[:,1].reshape(xx.shape).T, 10,colors='black', linewidths=0.5)
        # 添加颜色条
        cbar=plt.colorbar(heatmap,ax=axs[0,1],)
        num_ticks = 10  # 指定刻度的数量
        tick_values = np.linspace(uu_array[:,1].min(), uu_array[:,1].max(), num_ticks)
        tick_labels = [f'{val:.5f}' for val in tick_values]

        # 设置颜色条的刻度值和标签
        cbar.set_ticks(tick_values)
        cbar.set_ticklabels(tick_labels)

        # 添加轴标签
        axs[0,1].set_xlabel('r')
        axs[0,1].set_ylabel('z')
        axs[0,1].set_title('w')
        
        # axs[0,2].plot(history['train_loss'], label='training loss')
        # #axs[0,1].plot(history['valid_loss'], label='validation loss')
        # axs[0,2].set_title('loss during training')
        # axs[0,2].set_xlabel('epochs')
        # axs[0,2].set_ylabel('loss')
        # axs[0,2].set_yscale('log')
        # axs[0,2].legend()

        i=0 ; j=1
        for k in range(2,6):
            j=j+1
            if j>=3:
                i=i+1
                j=0
            heatmap=axs[i,j].pcolormesh(xx, yy, uu_array[:,k].reshape(xx.shape).T,cmap='rainbow')  # cmap是颜色映射，你可以根据需要选择
            contour_lines = axs[i,j].contour(xx, yy, uu_array[:,k].reshape(xx.shape).T, 10,colors='black', linewidths=0.5)
            # 添加颜色条
            cbar=plt.colorbar(heatmap,ax=axs[i,j],label='Disp')
            # 添加轴标签
            axs[i,j].set_xlabel('r')
            axs[i,j].set_ylabel('z')
            num_ticks = 10  # 指定刻度的数量
            tick_values = np.linspace(uu_array[:,k].min(), uu_array[:,k].max(), num_ticks)
            tick_labels = [f'{val:.5f}' for val in tick_values]

            # 设置颜色条的刻度值和标签
            cbar.set_ticks(tick_values)
            cbar.set_ticklabels(tick_labels)

        i=2; j=0
        
        heatmap=axs[i,j].pcolormesh(xx, yy, sigma_zr.reshape(xx.shape).T,cmap='rainbow')  # cmap是颜色映射，你可以根据需要选择
        contour_lines = axs[i,j].contour(xx, yy, sigma_zr.reshape(xx.shape).T, 10,colors='black', linewidths=0.5)
        # 添加颜色条
        cbar=plt.colorbar(heatmap,ax=axs[i,j])
        # 添加轴标签
        axs[i,j].set_xlabel('r')
        axs[i,j].set_ylabel('z')
        num_ticks = 10  # 指定刻度的数量
        max_zr=sigma_zr.max()
        min_zr=sigma_zr.min()
        tick_values = np.linspace(sigma_zr.min(), sigma_zr.max(), num_ticks)
        tick_labels = [f'{val:.5f}' for val in tick_values]
        # 设置颜色条的刻度值和标签
        cbar.set_ticks(tick_values)
        cbar.set_ticklabels(tick_labels)

        i=2; j=1
        
        heatmap=axs[i,j].pcolormesh(xx, yy, (sigma_zr-uu_array[:,5]).reshape(xx.shape).T,cmap='rainbow')  # cmap是颜色映射，你可以根据需要选择
        contour_lines = axs[i,j].contour(xx, yy, (sigma_zr-uu_array[:,5]).reshape(xx.shape).T, 10,colors='black', linewidths=0.5)
        # 添加颜色条
        cbar=plt.colorbar(heatmap,ax=axs[i,j])
        # 添加轴标签
        axs[i,j].set_xlabel('r')
        axs[i,j].set_ylabel('z')
        num_ticks = 10  # 指定刻度的数量
        tick_values = np.linspace((sigma_zr-uu_array[:,5]).min(),(sigma_zr-uu_array[:,5]).max(), num_ticks)
        tick_labels = [f'{val:.5f}' for val in tick_values]
        # 设置颜色条的刻度值和标签
        cbar.set_ticks(tick_values)
        cbar.set_ticklabels(tick_labels)


        i=2 ; j=1
        for metric_name, metric_values in history.items():
            if metric_name[:5]=="valid" or metric_name=="train_loss":
                continue
            j=j+1
            if j>=3:
                i=i+1
                j=0
            axs[i,j].plot(metric_values,label=metric_name)
            axs[i,j].set_title(metric_name)
            axs[i,j].set_xlabel('epochs')
            axs[i,j].set_ylabel('loss')
            axs[i,j].set_yscale('log')

        
        # points_generator=generator_2dspatial_segment(size=100, start=(0.0, 1.0), end=(1.0, 1.0),device=self.device,random=True)
        # x,y=next(points_generator)
        # u=approximator.__call__(x.requires_grad_(),y.requires_grad_())

        # u=u.detach().cpu().numpy()
        # x=x.detach().cpu().numpy()
        # axs[2,1].plot(x,u,label='predict')
        # axs[2,1].plot(x,2*x**3-3*x**2+1,label='exact')
        # axs[2,1].set_xlabel('r')
        # axs[2,1].set_ylabel('temprature')
        # axs[2,1].set_title('up_boundary_compare')
        # axs[2,1].legend()

        #fem=pd.read_csv('./data/comsol_data_2x3-3x2+1.txt',delimiter=r'\s+')
        #fem=pd.read_csv('./data/comsol_h_200.txt',delimiter=r'\s+')
        # fem=pd.read_csv('./data/h20000.txt',delimiter=r'\s+')
        # uu_di=abs(uu_array*self.args.maxf+303.15-fem['T'].values)
        # heatmap=axs[2,2].pcolormesh(xx, yy, uu_di.reshape(xx.shape).T, cmap='rainbow')
        # cbar=plt.colorbar(heatmap,ax=axs[2,2],label='Temperature(/K)')
        # # 添加轴标签
        # # 手动设置 colorbar 的刻度标签
        # cbar_ticks = [uu_di.min(), uu_di.max()]  # 设置刻度标签为最小值和最大值
        # cbar.set_ticks(cbar_ticks)

        # 设置刻度标签的文本，可以使用字符串格式化来显示具体值
        # cbar_ticklabels = [f'{tick:.2f}' for tick in cbar_ticks]
        # cbar.set_ticklabels(cbar_ticklabels)
        # axs[2,2].set_xlabel('r')
        # axs[2,2].set_ylabel('z')
        # axs[2,2].set_title('Heatmap_compare')

        #plt.legend()
        plt.tight_layout()
        plt.savefig(self.args.save_dict+"-image/"+str(epoch)+".png" , dpi=400)
        #print("Save successfully")
        #plt.show()
