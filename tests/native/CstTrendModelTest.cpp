#include "Engine/Visualization/Charts/CstTrendModel.hpp"
#include <stdexcept>
#include <limits>
#include <iostream>
using namespace combination;
void Check(bool value,const char* message) { if(!value) throw std::runtime_error(message); }
int main() {
    CstTrendModel m; m.SetData({0,1,121,122},{1,2,3,4},{2,3,4,5});
    Check(m.rows.size()==2 && m.rows.front()[0]==-1 && m.rows.back()[0]==0,"CST rolling cutoff and relative time");
    m.SetData({1,2},{1,std::numeric_limits<double>::quiet_NaN()},{2,3});
    Check(m.rows.size()==1,"Filter entire nonfinite row");
    Check(m.RawBounds()[0]==-1,"Single point uses CST fallback bounds");
    m.xLabel="EVALUATION"; m.relativeTime=false; m.SetData({4,5},{2,3},{3,4});
    Check(m.RawBounds()[0]==0,"Evaluation axis anchors zero");
    std::vector<double> x(1001),a(1001),b(1001); for(int i=0;i<1001;++i) x[i]=a[i]=b[i]=i;
    m.maxPoints=50; m.SetData(x,a,b); Check(m.rows.size()==50 && m.rows.front()[0]==0 && m.rows.back()[0]==1000,"CST bounded display points");
    Check(CstTrendModel::FormatTick(-1e-12,1)=="0.0","Negative zero normalization");
    std::cout<<"CST trend window, filtering, bounds, endpoints and ticks passed\n";
}
