#pragma once
#include <cstdio>
#include <string>
#include <vector>
namespace rk {
inline std::string& _buf(){ static std::string b; return b; }
inline void _key(const std::string& k){ if(!_buf().empty()) _buf()+=","; _buf()+="\""+k+"\":"; }
inline std::string _num(double v){ char s[64]; std::snprintf(s,sizeof s,"%.17g",v); return s; }
inline void emit(const std::string& k,double v){_key(k);_buf()+=_num(v);} inline void emit(const std::string& k,int v){_key(k);_buf()+=std::to_string(v);} inline void emit(const std::string& k,long v){_key(k);_buf()+=std::to_string(v);} inline void emit(const std::string& k,bool v){_key(k);_buf()+=v?"true":"false";} inline void emit(const std::string& k,const char* v){_key(k);_buf()+="\""+std::string(v)+"\"";} inline void emit(const std::string& k,const std::string& v){_key(k);_buf()+="\""+v+"\"";}
inline void emit(const std::string& k,const std::vector<double>& v){_key(k);_buf()+="[";for(size_t i=0;i<v.size();++i)_buf()+=(i?",":"")+_num(v[i]);_buf()+="]";}
inline int done(){std::fflush(stdout);std::printf("\n{%s}\n",_buf().c_str());std::fflush(stdout);return 0;}
}
