import { jwtDecode } from 'jwt-decode';

export interface DecodedToken {
    sub: string;
    active_org_id: string;
    role: string;
    token_version: number;
    exp: number;
}

export const setToken = (token: string) => {
    if (typeof window !== 'undefined') {
        localStorage.setItem('saarthi_token', token);
    }
};

export const getToken = (): string | null => {
    if (typeof window !== 'undefined') {
        return localStorage.getItem('saarthi_token');
    }
    return null;
};

export const removeToken = () => {
    if (typeof window !== 'undefined') {
        localStorage.removeItem('saarthi_token');
    }
};

export const getDecodedToken = (): DecodedToken | null => {
    const token = getToken();
    if (!token) return null;
    try {
        return jwtDecode<DecodedToken>(token);
    } catch (e) {
        return null;
    }
};

export const getActiveOrgId = (): string | null => {
    const decoded = getDecodedToken();
    return decoded ? decoded.active_org_id : null;
};

export const isAuthenticated = (): boolean => {
    const decoded = getDecodedToken();
    if (!decoded) return false;
    const now = Date.now() / 1000;
    return decoded.exp > now;
};

export const logout = () => {
    removeToken();
    if (typeof window !== 'undefined') {
        window.location.href = '/login';
    }
};
