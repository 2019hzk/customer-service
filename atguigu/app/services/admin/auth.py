import jwt
from fastapi import HTTPException, status

from atguigu.app.schemas.admin.user import CurrentUser
from atguigu.common.config import get_settings

"""
1. sdk提供的包

2. 三方的包

3. 自己包提供的
"""


class AuthService:
    """
    认证服务
    """

    def __init__(self):
        self.settings = get_settings()

    def get_authorized_user(self,
                            authorization: str | None,
                            *roles: str
                            ) -> CurrentUser:
        """
        职责：获取当前用户信息以及完成角色的校验
        :return:
        """

        # 1. 根据令牌获取用户信息
        current_user = self._get_current_user(authorization)

        # 2. 校验角色
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="用户访问无权限"
            )

        return current_user

    def _get_current_user(self, authorization: str | None) -> CurrentUser:
        # 1. 获取令牌
        access_token = self._extract_token(authorization)

        # 2. 根据令牌解密获取用户信息
        current_user = self.decode_access_token(access_token)

        return current_user

    def _extract_token(self, authorization: str | None) -> str:
        """
        职责：提取令牌
        :param authorization:
        :return:
        """
        if not authorization or not authorization.lower().startswith("bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="该用户未认证"
            )
        return authorization.split(" ", 1)[1]

    def decode_access_token(self, access_token: str) -> CurrentUser:

        payload = jwt.decode(access_token, self.settings.jwt_secret, algorithms=[self.settings.jwt_algorithm])

        return CurrentUser.model_validate(payload)

    def encode_access_token(self, current_user: CurrentUser) -> str:
        # return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        access_token = jwt.encode(current_user.model_dump(),
                                  self.settings.internal_service_jwt_secret,
                                  self.settings.internal_service_jwt_algorithm)
        return access_token
