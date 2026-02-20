import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { toast } from 'sonner';
import { Building2 } from 'lucide-react';

export const AuthPage = () => {
  const { login, register } = useAuth();
  const [isLoading, setIsLoading] = useState(false);

  const [loginData, setLoginData] = useState({ email: '', password: '' });
  const [registerData, setRegisterData] = useState({ email: '', password: '', name: '' });

  const handleLogin = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      await login(loginData.email, loginData.password);
      toast.success('Welcome back!');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Login failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      await register(registerData.email, registerData.password, registerData.name);
      toast.success('Account created successfully!');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Registration failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen auth-bg flex items-center justify-center p-6">
      <div className="relative z-10 w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gradient-to-br from-amber-400 to-amber-600 mb-4 gold-glow">
            <Building2 className="w-8 h-8 text-slate-950" />
          </div>
          <h1 className="text-4xl font-bold gradient-text mb-2">Saudi Equity Nexus</h1>
          <p className="text-slate-400">Professional Investment Analysis Platform</p>
        </div>

        <Card className="glass-card border-white/10">
          <CardHeader>
            <CardTitle className="text-2xl text-white">Get Started</CardTitle>
            <CardDescription className="text-slate-400">Sign in or create an account to continue</CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="login" className="w-full">
              <TabsList className="grid w-full grid-cols-2 bg-slate-800/50">
                <TabsTrigger value="login" data-testid="login-tab">Login</TabsTrigger>
                <TabsTrigger value="register" data-testid="register-tab">Register</TabsTrigger>
              </TabsList>

              <TabsContent value="login" data-testid="login-form">
                <form onSubmit={handleLogin} className="space-y-4 mt-4">
                  <div className="space-y-2">
                    <Label htmlFor="login-email" className="text-slate-300">Email</Label>
                    <Input
                      id="login-email"
                      data-testid="login-email"
                      type="email"
                      placeholder="investor@example.com"
                      value={loginData.email}
                      onChange={(e) => setLoginData({ ...loginData, email: e.target.value })}
                      className="bg-slate-900/50 border-slate-700 focus:border-amber-400 focus:ring-amber-400/20 text-white"
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="login-password" className="text-slate-300">Password</Label>
                    <Input
                      id="login-password"
                      data-testid="login-password"
                      type="password"
                      value={loginData.password}
                      onChange={(e) => setLoginData({ ...loginData, password: e.target.value })}
                      className="bg-slate-900/50 border-slate-700 focus:border-amber-400 focus:ring-amber-400/20 text-white"
                      required
                    />
                  </div>
                  <Button
                    type="submit"
                    data-testid="login-submit-button"
                    className="w-full bg-gradient-to-r from-amber-400 to-amber-600 hover:from-amber-500 hover:to-amber-700 text-slate-950 font-bold"
                    disabled={isLoading}
                  >
                    {isLoading ? 'Signing in...' : 'Sign In'}
                  </Button>
                </form>
              </TabsContent>

              <TabsContent value="register" data-testid="register-form">
                <form onSubmit={handleRegister} className="space-y-4 mt-4">
                  <div className="space-y-2">
                    <Label htmlFor="register-name" className="text-slate-300">Full Name</Label>
                    <Input
                      id="register-name"
                      data-testid="register-name"
                      type="text"
                      placeholder="Ahmed Al-Saud"
                      value={registerData.name}
                      onChange={(e) => setRegisterData({ ...registerData, name: e.target.value })}
                      className="bg-slate-900/50 border-slate-700 focus:border-amber-400 focus:ring-amber-400/20 text-white"
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="register-email" className="text-slate-300">Email</Label>
                    <Input
                      id="register-email"
                      data-testid="register-email"
                      type="email"
                      placeholder="investor@example.com"
                      value={registerData.email}
                      onChange={(e) => setRegisterData({ ...registerData, email: e.target.value })}
                      className="bg-slate-900/50 border-slate-700 focus:border-amber-400 focus:ring-amber-400/20 text-white"
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="register-password" className="text-slate-300">Password</Label>
                    <Input
                      id="register-password"
                      data-testid="register-password"
                      type="password"
                      value={registerData.password}
                      onChange={(e) => setRegisterData({ ...registerData, password: e.target.value })}
                      className="bg-slate-900/50 border-slate-700 focus:border-amber-400 focus:ring-amber-400/20 text-white"
                      required
                    />
                  </div>
                  <Button
                    type="submit"
                    data-testid="register-submit-button"
                    className="w-full bg-gradient-to-r from-amber-400 to-amber-600 hover:from-amber-500 hover:to-amber-700 text-slate-950 font-bold"
                    disabled={isLoading}
                  >
                    {isLoading ? 'Creating account...' : 'Create Account'}
                  </Button>
                </form>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default AuthPage;
