
if __name__ == '__main__':
	from app.tasks import monday as mon_tasks
	mon_tasks.stock_control.build_daily_orders()
