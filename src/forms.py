from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DateTimeField, IntegerField, SelectField, FileField, SubmitField, SelectMultipleField
from wtforms.validators import DataRequired, Length, Optional, NumberRange
from flask_wtf.file import FileAllowed
from .models import Tag  # Import the Tag model

class ActivityForm(FlaskForm):
    title = StringField('活动标题', validators=[DataRequired(), Length(min=2, max=100)])
    description = TextAreaField('活动描述', validators=[DataRequired()])
    location = StringField('活动地点', validators=[DataRequired(), Length(max=100)])
    start_time = DateTimeField('开始时间', format='%Y-%m-%d %H:%M', validators=[DataRequired()])
    end_time = DateTimeField('结束时间', format='%Y-%m-%d %H:%M', validators=[DataRequired()])
    registration_deadline = DateTimeField('报名截止时间', format='%Y-%m-%d %H:%M', validators=[DataRequired()])
    max_participants = IntegerField('最大参与人数', validators=[Optional(), NumberRange(min=0)])
    poster = FileField('活动海报', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], '只允许上传图片文件!')
    ])
    status = SelectField('活动状态', choices=[
        ('active', '进行中'),
        ('completed', '已结束'),
        ('cancelled', '已取消')
    ], validators=[DataRequired()])
    tags = SelectMultipleField('活动标签', choices=[], coerce=int)
    submit = SubmitField('保存')

class SearchForm(FlaskForm):
    query = StringField('搜索', validators=[Optional(), Length(max=100)])
    category = SelectField('类别', choices=[
        ('all', '全部'),
        ('title', '标题'),
        ('location', '地点'),
        ('description', '描述')
    ], validators=[Optional()])
