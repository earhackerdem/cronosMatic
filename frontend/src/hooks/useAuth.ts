import {
  type QueryClient,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query"
import { useNavigate } from "@tanstack/react-router"

import {
  type Body_login_login_access_token as AccessToken,
  LoginService,
  type UserPublic,
  type UserRegister,
  UsersService,
} from "@/client"
import { handleError } from "@/utils"
import useCustomToast from "./useCustomToast"

const ACCESS_TOKEN_KEY = "access_token"
const CURRENT_USER_QUERY_KEY = ["currentUser"] as const

const isLoggedIn = () => {
  return localStorage.getItem(ACCESS_TOKEN_KEY) !== null
}

const persistGoogleToken = (token: string, queryClient: QueryClient) => {
  localStorage.setItem(ACCESS_TOKEN_KEY, token)
  queryClient.invalidateQueries({ queryKey: CURRENT_USER_QUERY_KEY })
}

const useAuth = () => {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { showErrorToast } = useCustomToast()

  const { data: user } = useQuery<UserPublic | null, Error>({
    queryKey: CURRENT_USER_QUERY_KEY,
    queryFn: UsersService.readUserMe,
    enabled: isLoggedIn(),
  })

  const signUpMutation = useMutation({
    mutationFn: (data: UserRegister) =>
      UsersService.registerUser({ requestBody: data }),
    onSuccess: () => {
      navigate({ to: "/login" })
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] })
    },
  })

  const login = async (data: AccessToken) => {
    const response = await LoginService.loginAccessToken({
      formData: data,
    })
    localStorage.setItem(ACCESS_TOKEN_KEY, response.access_token)
  }

  const loginMutation = useMutation({
    mutationFn: login,
    onSuccess: () => {
      navigate({ to: "/" })
    },
    onError: handleError.bind(showErrorToast),
  })

  const loginWithGoogleToken = (token: string) => {
    persistGoogleToken(token, queryClient)
  }

  const logout = () => {
    localStorage.removeItem(ACCESS_TOKEN_KEY)
    navigate({ to: "/login" })
  }

  return {
    signUpMutation,
    loginMutation,
    loginWithGoogleToken,
    logout,
    user,
  }
}

export { isLoggedIn, persistGoogleToken }
export default useAuth
