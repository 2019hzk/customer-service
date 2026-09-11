from atguigu.app.schemas.user import CurrentUser


class AuthService:
    """
    认证服务
    """

    def get_current_user(self, authorization: str | None) -> CurrentUser:
        """
        职责：获取当前用户信息以及完成角色的校验
        :return:
        """
        pass


