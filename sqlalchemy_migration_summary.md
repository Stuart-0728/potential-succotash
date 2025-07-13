# SQLAlchemy 2.0查询语法迁移总结

## 背景

项目之前使用的是旧版SQLAlchemy查询语法（如`Model.query.get(id)`），这种语法在新版SQLAlchemy中已被弃用，并会导致`AttributeError: ... has no attribute 'query'`错误。本次迁移将所有查询更新为SQLAlchemy 2.0兼容的语法。

## 更新内容

我们创建了一个自动化脚本`update_sqlalchemy_queries.py`，对项目中的所有Python文件进行了扫描和更新。脚本主要进行了以下类型的替换：

1. `Model.query.get(id)` → `db.session.get(Model, id)`
2. `Model.query.get_or_404(id)` → `db.get_or_404(Model, id)`
3. `Model.query.filter_by(...).first()` → `db.session.execute(db.select(Model).filter_by(...)).scalar_one_or_none()`
4. `Model.query.filter(...).first()` → `db.session.execute(db.select(Model).filter(...)).scalar_one_or_none()`
5. `Model.query.filter_by(...).all()` → `db.session.execute(db.select(Model).filter_by(...)).scalars().all()`
6. `Model.query.filter(...).all()` → `db.session.execute(db.select(Model).filter(...)).scalars().all()`
7. `Model.query.all()` → `db.session.execute(db.select(Model)).scalars().all()`
8. `Model.query.filter_by(...).count()` → `db.session.execute(db.select(func.count()).select_from(Model).filter_by(...)).scalar()`
9. `Model.query.filter(...).count()` → `db.session.execute(db.select(func.count()).select_from(Model).filter(...)).scalar()`
10. `Model.query.count()` → `db.session.execute(db.select(func.count()).select_from(Model)).scalar()`
11. `Model.query.order_by(...).all()` → `db.session.execute(db.select(Model).order_by(...)).scalars().all()`
12. `Model.query.order_by(...).first()` → `db.session.execute(db.select(Model).order_by(...)).scalar_one_or_none()`
13. `Model.query.order_by(...).limit(...).all()` → `db.session.execute(db.select(Model).order_by(...).limit(...)).scalars().all()`
14. `Model.query.paginate(...)` → `db.paginate(db.select(Model), ...)`
15. `Model.query.filter_by(...).paginate(...)` → `db.paginate(db.select(Model).filter_by(...), ...)`
16. `Model.query.filter(...).paginate(...)` → `db.paginate(db.select(Model).filter(...), ...)`
17. `Model.query.filter_by(...).order_by(...).paginate(...)` → `db.paginate(db.select(Model).filter_by(...).order_by(...), ...)`
18. `Model.query.filter(...).order_by(...).paginate(...)` → `db.paginate(db.select(Model).filter(...).order_by(...), ...)`
19. `Model.query.order_by(...).paginate(...)` → `db.paginate(db.select(Model).order_by(...), ...)`

## 更新的文件

脚本共更新了12个文件：

1. `/Users/luoyixin/Desktop/cqnu_association/fix_auth_routes.py`
2. `/Users/luoyixin/Desktop/cqnu_association/debug_messages.py`
3. `/Users/luoyixin/Desktop/cqnu_association/create_simple_admin.py`
4. `/Users/luoyixin/Desktop/cqnu_association/fix_missing_columns.py`
5. `/Users/luoyixin/Desktop/cqnu_association/create_test_activity_simple.py`
6. `/Users/luoyixin/Desktop/cqnu_association/fix_checkin_route.py`
7. `/Users/luoyixin/Desktop/cqnu_association/init_db.py`
8. `/Users/luoyixin/Desktop/cqnu_association/src/__init__.py`
9. `/Users/luoyixin/Desktop/cqnu_association/src/routes/admin.py`
10. `/Users/luoyixin/Desktop/cqnu_association/src/routes/utils.py`
11. `/Users/luoyixin/Desktop/cqnu_association/src/routes/student.py`
12. `/Users/luoyixin/Desktop/cqnu_association/src/routes/tag.py`

每个文件都已备份为`.bak`文件，以便在需要时可以恢复原始版本。

## 注意事项

1. 在使用新的查询语法时，需要确保导入了必要的模块：
   ```python
   from sqlalchemy import select, func
   ```

2. 对于分页查询，需要使用`db.paginate`而不是`.paginate()`方法。

3. 对于计数查询，需要使用`func.count()`函数。

4. 在某些情况下，可能需要手动调整查询逻辑，特别是涉及复杂的联表查询或子查询。

## 后续工作

1. 对于任何新添加的代码，都应该使用新的SQLAlchemy 2.0查询语法。

2. 如果在运行过程中发现任何查询相关的错误，可以参考上述替换规则进行手动修复。

3. 建议在项目文档中添加SQLAlchemy 2.0查询语法的使用指南，以便团队成员遵循统一的编码风格。 