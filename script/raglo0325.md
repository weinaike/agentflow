...
(14)
where F is the total ﬂux,r0 is the scale radius, andβtypically
ranges from 2 to 5. In the limitβ→ ∞, the Moffat proﬁle tends
towards a Gaussian.
It is represented in GAL SIM by theMoffatclass, and the
size can be speciﬁed usingr0, the full-width at half-maximum
(FWHM), or the half-light radius. It is also possible to specify
a truncation radius for the Moffat proﬁle, rather than allowit to
extend indeﬁnitely.
3.2.4. The Kolmogorov proﬁle
In a long ground-based exposure, the PSF is predicted to fol-
low a particular functional form due to the Kolmogorov spec-
trum of turbulence in the atmosphere. Racine (1996) showed
that this prediction was indeed a better ﬁt to the observations of
stars in long exposures than a Moffat proﬁle.
The surface brightness of a Kolmogorov proﬁle is deﬁned in
Fourier space as
˜I(k)= F e−(k/k0)5/3
, (15)
where F is the total ﬂux,k0 = Aλ/r0,A ≃ 2.99 is a constant
given by Fried (1966), and herer0 is the Fried parameter (to
be distinguished from the use ofr0 to denote the scale radius in
other proﬁles). Typical values for the Fried parameter are on the
order of 10 cm for most observatories and up to 20 cm for ex-

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    cellent sites. The values are usually quoted atλ= 500 nm, and
the Fried parameterr0 depends on wavelength asr0 ∝ λ−6/5.
This proﬁle is represented in GAL SIM by theKolmogorov
class, and the size can be speciﬁed usingλ/r0, the FWHM, or
the half-light radius.
3.3. Generic models
3.3.1. The Gaussian proﬁle
The Gaussian proﬁle has convenient properties: it is rel-
atively compact and analytic in both real space and Fourier
space, and convolutions of Gaussian proﬁles can themselvesbe
written as a new Gaussian proﬁle. Observational propertiesof
Gaussian proﬁles, such as their second moments, are also typi-
cally analytic.
For this reason the Gaussian proﬁle is often used to represent
galaxies and PSFs in simple simulations where speed is valued
above realism. And thanks to its analytic properties, it hasgreat
value for testing purposes. Furthermore, while a single Gaus-
sian proﬁle is generally a poor approximation to both real PSFs
and real galaxies, linear superpositions of Gaussian proﬁles can
be used to approximate realistic proﬁles with much greater ac-
curacy (e.g. Hogg & Lang, 2013; Sheldon, 2014).
The surface brightness of a Gaussian proﬁle varies as
I(r)= F
2πσ2 e−r2/2σ2
, (16)
where F is the total ﬂux andσis the usual Gaussian scale pa-
rameter.
It is represented in GAL SIM by theGaussianclass, and
the size can be speciﬁed usingσ, the FWHM, or the half-light
radius.
3.3.2. Shapelet proﬁles
Shapelets were developed independently by
Bernstein & Jarvis (2002) and Refregier (2003) as an ef-
fective means of characterizing compact surface brightness
proﬁles such as galaxies or stars. The shapelets basis set
consists of two-dimensional Gaussian proﬁles multiplied by
polynomials, and they have a number of useful properties. For
example, they constitute a complete basis set, so in theory any
image can be decomposed into a shapelet vector; however,
proﬁles that are not well matched to the size of the Gaussian
will require very high order shapelet terms, such that the
decomposition is unfeasible in practice (e.g. Melchior et al.,

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    2010).
For images that are relatively well approximated by a Gaus-
sian, they provide a compact representation of the object, since
most of the information in the image is described by low order
corrections to the Gaussian, which is what the shapelet decom-
position provides.
The Shapeletclass in GAL SIM follows the notation
of Bernstein & Jarvis (2002), although it is also similar to
what has been called “polar shapelets” by Massey & Refregier
(2005). The shapelet expansion is indexed by two numbers,p
and q19:
I(r,θ)=
∑
p,q≥0
bpqψσ
pq(r,θ) (17)
19 The shapelet functions happen to be eigenfunctions of the 2Dquantum
harmonic oscillator. In that framework,p and q count the number of quanta
with positive and negative angular momentum, respectively. N = p + q is the
total energy andm = p −q is the net angular momentum.
6
ψσ
pq(r,θ)= (−1)q
√πσ2
√
q!
p!
( r
σ
) m
eim θe−r2/2σ2
×L(m )
q (r2/σ2) ( p ≥ q) (18)
ψσ
qp(r,θ)=
ψσpq(r,θ) (19)
m ≡ p −q. (20)
L(m )
q (x) are the Laguerre polynomials, which satisfy the recur-
rence relation:
L(m )
0 (x)= 1 (21)
L(m )
1 (x)= (m +1)− x (22)
(q +1)L(m )
q+1(x)= [(2q +m +1)− x]L(m )
q (x)
−(q +m )L(m )
q−1(x). (23)
The functions may also be indexed byN = p + q and m =
p − q, which is sometimes more convenient. Both indexing
conventions are implemented in GAL SIM .
One of the handy features of shapelets is that their Fourier
transforms are also shapelets:
˜ψσ
pq(k,φ)= (−i)m
√π
√
q!
p!(kσ)m eim φe−k2σ2/2
×L(m )
q (k2σ2) ( p ≥ q). (24)
This means convolving shapelets in Fourier space is very efﬁ-
cient.
3.3.3. Interpolated images
In some cases, it is useful to be able to take a given image
and treat it as a surface brightness proﬁle. This requires deﬁning
how to interpolate between the pixel values at which the surface
brightness is sampled.
One application for this is the use of direct observations of
individual galaxies (e.g., fromHST ) as the models for further
simulations, already mentioned in §3.1.4. See §6.5 for more
about this possibility.

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    Another application was also mentioned above in §3.2.2. The
general aberrated optical PSF is too complicated to model ana-
lytically, so theOpticalPSFclass is internally evaluated by
interpolation over a ﬁnite grid of samples of the surface bright-
ness proﬁle.
The InterpolatedImageclass converts an arbitraryn×n
image array with elementsIi jon pixels of sizes into a continu-
ous surface brightness distribution
I(x,y)=
∑
i,j
Ii jκ(x/s−i,y/s−j), (25)
where κ is a real-space kernel chosen from those listed in Ta-
ble 1. Each interpolant usesK ×K input pixel values around the
given (x,y) to render a sample at that location. Rendering an
M × M output image hence requiresK 2 M 2 operations, and the
footprint of theInterpolatedImageis extended byKs /2
beyond the original input image.
The delta-function kernel yields inﬁnite (or zero) values in
direct rendering and is hence a highly ill-advised choice for
an InterpolatedImagethat is to be rendered without fur-
ther convolutions. The sinc kernel has inﬁnite extent and hence
uses allN ×N input samples to reconstruct each output sample,
leading toN 2 M 2 operations in a direct-space rendering. In a
high-volume simulation this will also be ill-advised. Approxi-
mations to the sinc kernel that provide ﬁnite support are often
found to give a good compromise. Examples include the kernel
that represents cubic and quintic (i.e. 3rd and 5th order) poly-
nomial interpolation, and the Lanczos kernel (see Table 1, also
Bernstein & Gruen, 2014). As will be demonstrated in §9.2
and §9.3, these higher-order interpolation kernels meet strin-
gent performance requirements for the representation of galaxy
images.
3.4. Transformations
Many of the proﬁles we have described so far are circularly
symmetric and centred on the coordinate origin. GAL SIM can,
however, use these proﬁles to represent (for example) ellipti-
cal, off-centred surface brightness proﬁles. Various transforma-
tions can be applied to a GAL SIM object representing a surface
brightness distributionI(x), to return a new object representing

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    I′(x).
The overall amplitude of the proﬁle can be rescaled by some
factor simply by using the*operator. It is also possible to get
a rescaled proﬁle with a speciﬁed value for the new total ﬂux.
Either way, the new proﬁle isI′(x)= cI(x) for some constantc.
Any one-to-one transformationT of the plane deﬁnes an im-
age transformation via
I′(x)= I
[
T −1(x)
]
. (26)
The G AL SIM operationtransformimplements local linear
transformations deﬁned by a transformation matrixA as
T (x)= Ax . (27)
This can account for any arbitrary distortion, rotation, parity ﬂip
or expansion of the coordinate system. The user can specifyA
directly; alternatively the GAL SIM operationsrotate, ex-
pand, magnify, shear,and lensimplement restricted
versions of the transformation that are often convenient inprac-
tice.
There is also a command calleddilatethat combines an
expansion of the linear size (i.e.A being a multiple of the iden-
tity matrix) with an amplitude scale factor to keep the overall
ﬂux of the resulting proﬁle unchanged. This is merely a con-
venience function, but it is handy, since this operation is fairly
common.
Finally, theshiftfunction can translate the entire proﬁle
by some amountx0. This corresponds to the transformation
T (x)= x +x0. (28)
Together,shiftand transformenable any arbitrary afﬁne
transformation.
7
Table 1: Properties of interpolants
Name Formula Notes a No. of pointsK
Delta δ(x) Cannot be rendered in x domain; extreme aliasing∝ 1. 0,1
Nearest 1, |x| <1/2 Aliasing ∝ k−1 1
Linear 1 −| x|, |x| <1 Aliasing ∝ k−2 2
Cubic piecewise cubicb Common choice forK 4
Quintic piecewise quinticb Optimized choice forK k (cf. §6.2.4) 6
Lanczos sincx sinc(x/n), |x| <n Common choice forK withn = 3–5 2n
SincInterpolantsincx Perfect band-limited interpolation; slowest ∞
aCoordinate distance from the origin in Fourier space is denotedk.
bFormulae forCubicand Quinticinterpolants are given in the Appendix to Bernstein & Gruen (2014).
All of these operations are implemented in GAL SIM via a

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    wrapper object that exists independently of, and interfaces with,
the original proﬁle. This means the code for implementing
these transformations (e.g. the effect in Fourier space, orthe de-
ﬂections to apply for photon shooting, see §6.3) exists in a sin-
gle place, which helps minimize unnecessary duplication and
ensure the reliability of the transformation routines.
For reasons discussed in §6, GAL SIM does not currently han-
dle non-afﬁne transformations acting on a single proﬁle (asre-
quired by simulations of ﬂexion such as Velander et al., 2011;
Rowe et al., 2013), but see §5 for how to handle such coordi-
nate transformation across a full image, using the appropriate
locally linear approximation at the location of each object.
3.5. Compositions
Two or more individual surface brightness proﬁles may be
added together using the+operator to obtain a proﬁle with
I′(x)= I1(x)+I2(x)+... .
The convolution of two or more objectsI1,I2 is deﬁned as
usual via
I′(x)= (I1 ◦I2)(x)=
∫
I1(x′)I2(x −x′) d2x′. (29)
This is implemented in GAL SIM with theConvolvefunction,
which takes a list of two or more objects to be convolved to-
gether.
There are also two special functions that can afford some
modest efﬁciency gains if they apply.AutoConvolveper-
forms a convolution of an object with itself, i.e. withI2(x) =
I1(x) in equation (29).AutoCorrelateperforms a con-
volution of an object with a 180◦ rotation of itself, i.e. with
I2(x)= I1(−x).
Finally, GAL SIM can implement a deconvolution as well.
This lets users solve for the solutionI′ to the equationI1 =
I′ ◦I2, which in Fourier space is simply
˜I′(k)= ˜I1(k)/˜I2(k) (30)
The functionDeconvolveimplements the inverse of a proﬁle
(e.g.I2 above) in Fourier space, which is a deconvolution in
real space. The returned object is not something that can be
rendered directly. It must be convolved by some other proﬁleto
produce something renderable (I1 in this example).
One common use case for this is to deconvolve an observed
image (represented by anInterpolatedImageobject) by

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    its original PSF and pixel response, producing an object that
would then be reconvolved by some other PSF corresponding to
a different telescope and rendered on an image with a new pixel
scale. This is the functionality at the heart of GAL SIM ’s imple-
mentation of the reconvolution algorithm described in §6.5and
used by theRealGalaxyclass (§3.1.4). As will be discussed
in §6.5, the latter PSF must be band-limited at a lower spatial
frequency than the original (deconvolved) PSF to avoid serious
artifacts in the ﬁnal image.
3.6. Chromatic objects
Real astronomical stars and galaxies have wavelength-
dependent intensity distributions. To model this, it is possible in
G AL SIM to deﬁne objects whose surface brightness is a func-
tion not only of position, but also of wavelength. These objects
can then be rendered as seen through a particular bandpass (the
throughput as a function of wavelength).
The simplest of the wavelength-dependent classes is the
Chromaticclass, which is constructed from an achromatic
proﬁle (i.e. any of the proﬁles described above) and a Spec-
tral Energy Distribution (SED). The SED deﬁnes a wavelength-
dependent ﬂux for the object.
Chromatic objects can be transformed, added, and convolved
using precisely the same syntax as for achromatic objects. The
addition of multiple chromatic objects provides a simple way to
creating galaxies with non-trivial wavelength-dependentmor-
phologies. A bulge and a disk can have different SEDs; star
forming regions or HII regions can also be added in with their
own SEDs.
In addition, the various transformations can take functions of
wavelength for their arguments. For example, differentialchro-
matic refraction is implemented by a wavelength-dependent
shift, and the effects of chromatic variation in Kolmogorov
turbulence can be approximately modelled with a wavelength-
dependent dilation. GAL SIM provides the helper function
ChromaticAtmosphere, which encapsulates both of these
effects for an atmospheric PSF.
A more detailed discussion of this recent addition to

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    the G AL SIM toolkit is reserved for future work, but it
provides a valuable resource for simulating a number of
important wavelength-dependent effects in cosmology (e.g.
8
Cypriano et al., 2010; V oigt et al., 2012; Plazas & Bernstein,
2012; Semboloni et al., 2013; Meyers & Burchat, 2014).
4. Lensing shear and magniﬁcation
A primary purpose of GAL SIM is to make simulated images
that can be used to test weak gravitational lensing data analy-
sis algorithms, which means that a framework for simulating
lensing shear and convergence (see, e.g., Schneider, 2006,for
a review) is critical. In the weak gravitational lensing limit, the
transformation between unlensed coordinates (xu,yu; with the
origin taken to be at the center of a distant galaxy light source)
and the lensed coordinates in which we observe galaxies (xl,yl;
with the origin at the center of the observed image) is linear:
( xu
yu
)
=
( 1 −γ1 −κ −γ2
−γ2 1 +γ1 −κ
)( xl
yl
)
. (31)
Here we have introduced the two components of lensing shear
γ1 and γ2, and the lensing convergenceκ. The shear describes
the anisotropic stretching of galaxy images in weak lensing.
The convergenceκ describes an isotropic change in apparent
object size: areas of the sky for whichκ is non-zero have ap-
parent changes in area (at ﬁxed surface brightness). Lensing
magniﬁcation is produced from a combination of the shear and
convergence.
It is worth noting that even whenκ = 0 the transformation
matrix in equation (31) will not have a unit determinant in gen-
eral. Object area (and thus ﬂux when conserving surface bright-
ness) is therefore not conserved by weak lensing shear, an effect
which is not always desired when simulating images. For con-
venience, GAL SIM implements a unit determinant shear trans-
formation that conserves object area, while also implement-
ing the non-area conserving shear deﬁned by the weak lensing
transformation of equation (31).
In the simplest use case, GAL SIM will take single values for
the lensing shear and convergence and apply them to objects.In

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    addition, however, GAL SIM is able to generate ﬁelds of coher-
ent shear and convergence values corresponding to two physical
scenarios described below: cosmological weak lensing ﬁelds
with some power spectrum, and the weak lensing that arises
from a spherical NFW halo (Navarro, Frenk, & White, 1996).
4.1. Cosmological lensing ﬁelds
G AL SIM provides routines to simulate a Gaussian random
ﬁeld approximation to a cosmological lensing signal, charac-
terized wholly by its power spectrum. In reality, shear and con-
vergence ﬁelds show signiﬁcant non-Gaussianity. The inten-
tion, therefore, is not highly cosmologically accurate shear and
convergence ﬁelds, such as would be suitable for an end-to-end
test of cosmological parameter determination. The intention is
rather to provide basic functionality for making semi-realistic,
spatially varying lensing ﬁelds so as to be able to test measure-
ment algorithms that ﬁnd such regimes challenging in general.
There is nothing to prevent any user from using outputs
from a more realistic cosmological ray-tracing simulation(e.g.
Becker, 2013) to create an observed galaxy shape catalog that
includes a realistic shear and convergence ﬁeld. If realismis
required, this procedure should be followed.
4.1.1. Basic capabilities
Any shear ﬁeld can be projected into orthogonalE - andB-
mode components, named for their similarity to the electromag-
netic vector ﬁelds with zero curl and zero divergence, respec-
tively (see, e.g. Schneider, 2006; Mandelbaum et al., 2014).
G AL SIM is capable of taking inputE - andB-mode shear power
spectra as user supplied functions, and generating random re-
alizations of shear and convergence ﬁelds drawn from those
power spectra. The basic functionality is carried out by the
PowerSpectrumclass. Shears are generated on a grid of
positions, but GAL SIM can interpolate to arbitrary positions
within the bounds of the grid using the interpolants discussed
in §6.2.
Observable quantities such as the shear correlation functions

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    are deﬁned using the vectors connecting pairs of galaxies atsep-
arationθ,
ξ±(θ)= ξ++(θ)±ξ××(θ) (32)
=
∫∞
0
1
2π[P E (k)±P B (k)]J0/4(kθ)k dk (33)
where J0/4 denotes the 0th and 4th Bessel function of the
ﬁrst kind, as is appropriate forξ+ and ξ−, respectively. See
Schneider et al. (2002) for more details about relating the cor-
relation functions to theE - andB-modes of the ﬂat-sky power
spectra20.
For cosmological shear correlationsP B ≃ 0 to a very good
approximation, although higher order effects (e.g. sourcered-
shift clustering) can introduce physical B-modes (see, e.g.,
Schneider, 2006). It is useful to includeP B when generating
shears for other purposes, such as when drawing atmospheric
PSF anisotropies according to some power spectrum (which
typically requires similar amounts ofE and B power). Here
P E (k) andP B (k) have dimensions of angle2; GAL SIM can ac-
cept the power spectra in various formats and sets of units.
These deﬁnitions of observables rely on continuous Fourier
transforms, but in practice we implement the calculations us-
ing discrete Fourier Transforms (DFT), and we must be care-
ful about the DFT conventions. We assume we have a grid
with lengthL along one dimension and spacingd between grid
points. Given a Fourier-space grid of size consistent with that
of the input real-space grid, the minimum and maximum one-
dimensional wavenumbers|k| on the grid arekmin = 2π/L and
kmax = π/d. The lensing engine ﬁnds the powerP(k) according
to the value ofk =
√
k2
1 +k2
2 on the grid, draws random ampli-
tudes from a Rayleigh distribution based on√P(k) and random
phases from a uniform distribution, and transforms back to our
real-space grid to get the real-space shear ﬁeld, with periodic
boundary conditions. The standard deﬁnition of the correlation
function (Eq. 33) uses the angular frequency, non-unitary deﬁ-
nition of the 1D Fourier transform:
˜f(k)=
∫∞
−∞
f(x)e−ikx dx ≡ F{ f(x)}; (34)
20Many standard references regarding lensing power spectra work in terms

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    of the spherical harmonicsℓ, with the power spectrum denotedC ℓ. In the ﬂat-
sky limit we can simply swapℓwith wavenumberk and C ℓ withP(k).
9
f(x)= 1
2π
∫∞
−∞
˜f(k)eikx dk ≡ F −1{˜
f(k)}. (35)
If we trace through the impact of this convention on the discrete,
ﬁnitely-sampled power spectrum, then our use of the NUM PY 21
package for Fourier transforms (with the more common unitary
deﬁnition of the DFT) necessitates various normalization fac-
tors related to the input grid conﬁguration. For further details,
see Appendix A.
4.1.2. Implementation details
Any DFT-based algorithm to generate shears according to
a power spectrum is subject to limitations due to the implicit
choice of a ﬁnite range in wavenumber and the difference be-
tween a discrete and continuous Fourier transform. GAL SIM
includes options to ameliorate these limitations:
• G AL SIM can optionally decrease (increase) the minimum
(maximum) value ofk by internally expanding (contract-
ing) the real-space grid before generating shears. This
helps avoid problems with missing shear power on vari-
ous scales; in the case of cosmological power spectra it is
particularly recommended for those who wish to properly
reproduce the large-scale shear correlation function (on
scales comparable to∼ 1/4 the total grid extent). There
is an important tradeoff implicit in the use of these op-
tions: the power spectra that result from using internally
enlarged grids is not strictly the same as the input one, and
there can beE and B mode leakage as a result of using
these options.
• G AL SIM has a utility to predict the shear correlation func-
tion resulting from the use of a limitedk range when gen-
erating shears. While the output is not exactly what will be
generated in reality since the algorithm does not account
for the use of a DFT, it permits users to assess in advance
whether their grid choices permit them to roughly repro-
duce shear correlations on the scales they want.
• A natural consequence of the limitedk range is that alias-

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    ing can occur if users supply a power spectrum with power
below the grid Nyquist scale. GAL SIM shear generation
routines can optionally band-limit the input power spec-
trum by applying a hard or soft cutoff at the Nyquist scale
to avoid aliasing.
4.1.3. Interpolation to non-gridded positions
After building a grid of shears and convergences, users can
interpolate them to arbitrary positions within the grid. However,
when using this functionality, some care must be employed to
prevent the interpolation procedure from spuriously modifying
the shear power spectrum or correlation function at scales of
interest.
The key effect of interpolation is to multiply the shear power
spectrum by a quantity proportional to the square of the Fourier
21http://www.numpy.org/
transform of the interpolant. As a result, we found that all inter-
polants modify the shear 2-point functions in a signiﬁcant way
(>10% but sometimes much more) for scales below 3 times the
original grid spacing. Thus, when interpolating shears to ran-
dom points, the grid spacing should be chosen with care, keep-
ing in mind the minimum scale above which the shear two-point
functions should be preserved. Edge effects can also be impor-
tant depending on the intended use for the resulting interpolated
shears and the choice of interpolant (see Table 1; §3.3.3).
4.2. Lensing by individual dark matter halos
The NFWHaloclass can produce shears and convergences
corresponding to a dark matter halo following a spherical NFW
(Navarro et al., 1996) proﬁle, using analytic formulae from
Bartelmann (1996) and Wright & Brainerd (2000). The formu-
lae depend on the cosmology being assumed, which in GAL SIM
is allowed to be an arbitraryΛCDM cosmology. It would not
be difﬁcult to extend this to more sophisticated cosmological
models.
The NFW lensing halo is deﬁned in terms of its mass, con-
centration, redshift, and position in the image. Then for any
given position and redshift of the source galaxy to be lensed, the
appropriate lensing quantities can be computed analytically. It

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    is, however, important to note that the implementation in GAL -
SIM adopts the coordinate frame of the observed galaxies, i.e.
no deﬂection angles are calculated or applied to galaxy posi-
tions. As a consequence the density of galaxies behind NFW
halos is not altered as would happen in nature. If needed, e.g.
for studies of magniﬁcation from galaxy clusters, this effect
should be taken into account.
5. World coordinate systems
The galaxy models described above are generally deﬁned in
terms of angular units on the sky. For example, a Sérsic proﬁle
might be constructed to have a half-light radius of 1.6 arcsec.
Before rendering this object onto an image, one must specify
how the image pixel coordinates relate to sky coordinates (also
known as world coordinates).
The simplest such relationship is to assign a pixel scale to the
image, typically in units of arcsec/pixel. However, this isnot
the only possible such relationship; in general, the “worldcoor-
dinates” on the sky can be rather complicated functions of the
image coordinates. GAL SIM allows for a variety of “world co-
ordinate systems” (WCS) ranging from a simple pixel scale to
the kinds of WCS functions typically found in the FITS (Flex-
ible Image Transport System, see e.g. Pence et al., 2010) head-
ers of real data images.
5.1. Types of WCS functions
The WCS classes used by GAL SIM can be broken into two
basic types: celestial and euclidean coordinate systems.
Celestial coordinate systems are deﬁned in terms of right as-
cension (RA) and declination (Dec). In GAL SIM this kind of
WCS is represented by subclasses ofCelestialWCS. This
10
includesRaDecFunction, which can represent any arbi-
trary function the user supplies for RA(x,y) and Dec(x,y), and
FitsWCS, which reads in the WCS information from a FITS
header.
Euclidean coordinate systems are deﬁned relative to a tangent
plane projection of the sky. Taking the sky coordinates to be
on an actual sphere with a particular radius, the tangent plane
would be tangent to that sphere. We use the labels (u,v) for the

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    coordinates in this system, where+v points north and+u points
west22.
In GAL SIM this kind of WCS is represented by subclasses of
EuclideanWCS. The most general isUVFunction, which
can represent any arbitrary function the user supplies foru(x,y)
and v(x,y).AffineTransformis the most generaluniform
coordinate transformation where all pixels have the same size
and shape, but that shape is an arbitrary parallelogram.
Other classes representing restricted specializations of
AffineTransformare available. The simplest one,Pix-
elScale, describes uniform square pixels. To date, this
is what has been used in simulations testing shear mea-
surement methods, including the most recent GREAT3 chal-
lenge (Mandelbaum et al., 2014), as well as all previous shear
testing projects (Heymans et al., 2006; Massey et al., 2007;
Bridle et al., 2010; Kitching et al., 2012, 2013). GAL SIM there-
fore makes it easy to ignore all of the WCS options and just use
a pixel scale instead. Any function that can take a WCS param-
eter, can also take a pixel scale parameter, which is interpreted
as aPixelScaleWCS.
5.2. Converting proﬁles
It is relatively straightforward to convert a surface brightness
proﬁle from the sky coordinates in which it is deﬁned to image
coordinates. We only need to assume that the ﬁrst derivatives
of the WCS functions are approximately constant over the size
of the object being modelled, which is generally a safe assump-
tion. That is, we use the local linear approximation of the WCS
transformation at the location of the object. Currently, GAL SIM
cannot accurately handle transformations that vary signiﬁcantly
over the size of the proﬁle being rendered; in fact this opera-
tion would be very similar to what is required for implementing
ﬂexion, and would most simply be incorporated in the context
of photon shooting (see §6.3).
The ﬁrst step if we are dealing with a celestial coordinate
system is to do a local tangent projection at the position of the
object. Speciﬁcally, we use the TAN projection described by

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    Calabretta & Greisen (2002), but it is likely that any of the tan-
gent plane projections discussed in that work would providean
equivalent conversion to a local Euclidean coordinate system.
The next step is to calculate the Jacobian of the WCS at the
location of the object:
J =
( du/dx du/dy
dv/dx dv/dy
)
(36)
22This can be counterintuitive to some, but it matches the viewfrom Earth.
When looking up into the sky, if north is up, then west is to theright.
This Jacobian deﬁnes the local afﬁne approximation of the
WCS at the location of the object, which we assume we can
take as uniform over the extent of the proﬁle we need to con-
vert.
Applying a general Jacobian transformation in GAL SIM was
described above in §3.4. Here, we are transforming from (u,v)
to (x,y), which means the transformation to be applied is really
J−1. To preserve the total ﬂux of the proﬁle, we also need to
multiply the resulting proﬁle by|detJ|.
The G AL SIM WCS classes have functionstoImageand
toWorldthat effect the conversion in either direction, using
whatever subset of the above steps are required for the given
WCS. If the WCS transformation is not uniform (so it matters
where the object is in the image), then the position of the object
(in either coordinate system) must be speciﬁed.
5.3. Integrating over pixels
While the galaxy proﬁles are naturally deﬁned in world co-
ordinates, the pixel response is most naturally deﬁned in image
coordinates, where it can typically be modelled as a unit square
top hat proﬁle. The PSF proﬁle may be more naturally consid-
ered in either coordinate system depending on where the model
is coming from. Thus, careful attention is required to handle all
of these correctly when using a complicated WCS.
We start by ignoring the PSF to show how to properly han-
dle a galaxy drawn onto uniform square pixels of dimension
s in an image (corresponding to aPixelScaleWCS). Let
the galaxy surface brightness be given in world coordinatesas
Iw (u,v). According to the methods in the previous section, the

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    corresponding proﬁle in image coordinates would be
Ii(x,y)= s2Iw (xs,ys) (37)
where s2 is the|detJ| factor mentioned above, which ensures
that the integral of each version of the proﬁle gives the same
total ﬂux.
The pixel response in the two coordinate systems is given by
a 2-dimensional top hat function with unit ﬂux:
Pw (u,v)= T s(u,v)≡







1
s2 |u|<s/2,|v|<s/2
0 otherwise (38)
Pi(x,y)= T1(x,y) (39)
in world and image coordinates respectively, where in the latter
the pixel size is, by deﬁnition, equal to 1.
When observed on an image, the galaxy’s surface brightness
proﬁle is integrated over the area of the pixel. In a particular
pixel (i, j), the integrated ﬂuxIi jis
Ii j=
∫is+s/2
is−s/2
∫ js+s/2
js−s/2
Iw (u,v) du dv (40)
=
∫+∞
−∞
∫+∞
−∞
s2Iw (u,v)Pw (is−u, js−v) du dv (41)
= s2(Iw ◦Pw )(is, js) (42)
=
∫+∞
−∞
∫+∞
−∞
Ii(x,y)Pi(i−x, j−y) dxdy (43)
11
= (Ii ◦Pi)(i, j) (44)
We thus ﬁnd thatIi jis the convolution of the galaxy proﬁle with
the pixel response evaluated at the centre of the pixel, and then
multiplied by the pixel area. Furthermore, this calculation can
be done in either coordinate system. This well-known result
(e.g. Lauer, 1999) is the basis of how GAL SIM implements the
integration of a surface brightness proﬁle over the pixel area.
For more complicated WCS functions, we can still apply the
same procedure. We either convert the galaxy proﬁle to image
coordinates and convolve by a unit square pixel, or convert the
unit square pixel to world coordinates and do the convolution
there. In GAL SIM thedrawImagemethod that performs the
rendering has access to the WCS of the image, and this convolu-
tion is handled automatically. The pattern adopted in the code is
to transform the galaxy proﬁle into image coordinates and then
convolve by a unit square pixel, but the converse would have
been equally valid.
For the PSF, when using a non-trivial WCS, some care is re-
quired regarding the coordinate system in which the PSF proﬁle
is deﬁned. The processes that cause the image coordinates to

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    become distorted from a square pixel are related to the causes
of the PSF, namely the atmosphere and the optics of the tele-
scope. Therefore, when choosing to apply a distorted WCS,
care is needed about whether the PSF is deﬁned in world or im-
age coordinates. If it is deﬁned in image coordinates, then it
should be converted to world coordinates (as described in §5.2)
prior to convolution by the galaxy proﬁle.
Finally, if a PSF is measured from an image, such as a real
data image of a star, then it already includes a convolution by
a pixel response23. To apply this consistently to simulated data
using the same WCS and pixel scale, an additional convolution
by a pixel should not be applied, since that would effectively
convolve by the pixel response twice. This kind of rendering
without the extra pixel convolution is possible in GAL SIM using
theno_pixeloption ofdrawImage.
6. Image rendering
A given object can be rendered onto an image (“drawn”)
through three methods in GAL SIM : direct drawing in real
space; drawing via discrete Fourier transform (DFT); or draw-
ing via “photon shooting,” whereby the surface brightness pro-
ﬁle is treated as a probability distribution, and a ﬁnite number
of “photons” sampled from this distribution are “shot” ontothe
image.
In principle all three rendering methods should be equivalent,
apart from the shot noise that is inherent to the photon-shooting
method. However, there is one additional difference that is
worth noting. The photon-shooting method bins the photons
according to the pixels they fall into and hence automatically
23 It is possible to remove the pixel response from the PSF imagewith the
Deconvolveoperator in GAL SIM which deconvolves by the original pixel.
This will only be numerically viable if the resulting objectis drawn onto an
image with pixels that are either the same size or (preferably) larger.
integrates the proﬁle over the pixels. Thus, theno_pixelop-
tion ofdrawImagementioned above in §5.3 will always use
either direct rendering or DFT as appropriate.

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    There are in practice also further minor differences between
the rendered output of the different methods that are due to ap-
proximations inherent to each technique. These we highlight
below.
Not all objects can be rendered with all three methods. In par-
ticular, convolution in real space is only implemented for con-
volution of two proﬁles, one of which is typically the pixel re-
sponse (cf. §6.1.5). Deconvolution (see §3.5; §6.5) is onlypos-
sible with the DFT method. Non-afﬁne transformations such
as ﬂexion (Goldberg & Bacon, 2005; Irwin & Shmakova, 2005;
Bacon et al., 2006) cannot be done in Fourier space; ﬂexion is
not currently implemented in GAL SIM for this reason. Table 2
summarizes the advantages and disadvantages of each render-
ing method.
6.1. Direct rendering
The default way to draw an object in GAL SIM is to integrate
its surface brightness over the pixel response by convolving the
object’s proﬁle with a square pixel (cf. §5.3). This means the
object that is actually being drawn will really be a convolution,
which is normally rendered using the DFT method (§6.2).
However, it is possible to tell GAL SIM not to convolve by
the pixel and instead draw the proﬁle directly by sampling the
surface brightness at the centre of each pixel. This is the easiest
rendering method to understand, so we describe it ﬁrst. But
of course, it does not directly correspond to a real image, so
the sum of the pixel values may not match the input ﬂux, for
instance.
6.1.1. Analytic objects
If an analytic surface brightness proﬁle is drawn without con-
volving by the pixel response, GAL SIM will use direct render-
ing, which just involves calculatingI(x,y) at the location of
each output pixel. The formulae forI(x,y) for our various an-
alytic objects were given in §3, and they are summarized in
Table 3.
Many objects have an analytic formula in real space, so
the direct rendering is straightforward. However, theKol-
mogorovproﬁle is only analytic in Fourier space, so the im-
plementation ofI(r) in real space uses a cubic spline lookup

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    table for the Hankel transform of˜I(k). This calculation is done
the ﬁrst time aKolmogorovobject is instantiated and saved
for any further instantiations, so the setup cost is only required
once.
For the radially symmetric proﬁles, we can take advantage
of the known symmetry to speed up the calculation. There are
also usually vectorization techniques that lead to furtherim-
provements in efﬁciency.
6.1.2. Shapelet proﬁles
The shapelet functions are not radially symmetric, but the
code to directly renderShapeletobjects uses fast recurrence
relations for the shapelet functions given in Bernstein & Jarvis
12
Table 2: Characteristics of different rendering methods
Characteristic Direct real-space Fourier Photon shooting
Operations for setupa 0 O (N 2 logN ) O (N 2 logN )
Operations for renderinga O (N 2) O (N 2 logN ) O (N γ logN )
Operations for additiona O (N 2) O (N 2) O (N γ)
Operations for convolutiona O (N 4)b O (N 2) O (N γ)
Operations for deconvolutiona impossible O (N 2) impossible
Easy to apply afﬁne transformations? yes yes yes
Easy to apply non-afﬁne transformations? yes no yes
Inaccuracies - band-limiting, folding shot noise, truncation
Fastest for analytic objects high S/N low S/N
aFor operation counts,N is the typical linear size of an input or output image, andN γ is the number of photons traced during photon shooting.
bDirect rendering can only handle convolution of two proﬁles.
Table 3: Analytic GAL SIM objects
Class name Real-space formula a Fourier-space formulaa Photon-shooting methodb
Exponential e−r/rs
(
1 +k2r2
s
) −3/2
Interval
DeVaucouleurse−7.669(r/re)1/4
LUT Interval
Sersic e−b(n)(r/re)1/n
LUT Interval
Airy
[ J1(ν)−ǫJ1(ǫν)
ν
] 2
, ν = πrD /λ Analyticc Interval
Moffat
(
1 + r2
r2
0
) −β
LUT d Analytic
Kolmogorov LUT e−(k/k0)5/3
Interval
Gaussian e−r2/2σ2
e−k2σ2/2 Analytic
Shapelet See §3.3.2 See §3.3.2 Not implemented
Pixel 1,|x| < s/2,|y| < s/2 sinc( skx) sinc(sky) Analytic
aNormalization factors have been omitted from the given formulae for brevity; the integral of the real-space proﬁle and the k = 0 value in Fourier space should both

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    equal the ﬂuxF of the object. “LUT” means that the function requires integrations that are precomputed and stored in a cubic-spline look-up table.
bThe photon-shooting methods are the following: “Analytic”means that photon locations are derived from a remapping of one or more uniform deviates intox;
“Interval” involves a combination of weighting and rejection sampling, as described in Section 6.3; “Not implemented”means that GAL SIM cannot currently
render this with photon shooting.
cFourier representation of the Airy function with obscuration is analytic but too complex for the table.
dFor genericβvalues, a lookup table is used. However, some particular values ofβhave analytic Fourier-space formulae, which GAL SIM uses in these cases.
13
(2002), which vectorize conveniently when applied to the pixels
in the image. They are thus also relatively efﬁcient to draw.
6.1.3. Interpolated images
InterpolatedImageobjects are usually the slowest to
directly render, since equation (25) involves a sum over a num-
ber of the original pixels for each output pixel value, the exact
number depending on the interpolant being used (see Table 1).
6.1.4. Transformations
All of the transformations described in §3.4 are very simple
to apply when directly rendering. The value of the transformed
proﬁle, including all three kinds of effects, is simply
I′(x)= c I
[
A −1(x −x0)
]
. (45)
where I(x) is the original proﬁle.
6.1.5. Compositions
Directly rendering a sum of proﬁles is trivial, since each pro-
ﬁle can be rendered individually, adding the ﬂux to whatever
has already been rendered.
The rendering of a convolution is almost always done via
DFT or photon-shooting methods. However, when convolving
two objects that are both known to have high-frequency con-
tent, such that an unaliased DFT is impractical, GAL SIM may
elect to render it directly through a Gauss-Kronrod-Patterson
evaluation of the convolution integral, equation (29).
Generally such circumstances do not represent any physi-
cally realizable image, since real telescopes and detectors lead

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    to band-limited images. However, in simulated images, it can
happen if two objects being convolved both have hard edges.
Here, a “hard edge” means a place where the surface brightness
abruptly drops from some ﬁnite value to zero. For example a
Pixelconvolved with a truncatedMoffatproﬁle would by
default be convolved using direct integration. In this and simi-
lar cases, the direct integration is generally both faster and more
accurate.
6.2. Discrete Fourier transform rendering
When rendering images that include convolution by a pixel
response (and often other proﬁles such as a PSF), GAL SIM uses
DFTs by default.
6.2.1. Band limiting and folding
To sample a surface brightness proﬁleI(x) onto anM × M
grid with sample pitch∆x via DFT, we will need to know its
Fourier transform˜I(k) at all points withkx,ky being multiples
of∆k = 2π/(M ∆x). If any frequency modes are present in˜I(k)
beyond the Nyquist frequencyπ/∆x of the output grid these
will be aliased in the output image, as required for the correct
rendering of undersampled data.
The input to the DFT will be theM × M Hermitian array of
Fourier coefﬁcients summed over all aliases:
˜ai j=
∑
p,q
˜I[ (i+ pM )∆k,(j+qM )∆k)] ,
− M /2 ≤ i, j< M /2. (46)
These sums must be truncated at some ﬁnite (p,q) range. We
must select a spatial frequencykmax such that we approximate
˜I(kx,ky) = 0 for|kx| > kmax or |ky| > kmax . Any real telescope
produces bandlimited images, transmitting zero power beyond
a wave vector ofkmax = 2πD /λ, whereD is the maximum en-
trance aperture dimension andλis the wavelength of observa-
tion. For space-based observations we are typically creating im-
ages sampled near the Nyquist scale ofλ/2D for this frequency,
and we can run the sum (46) over all physically realizable fre-
quencies without approximation.
For ground-based observations, the PSF is typically much
larger than the diffraction limit, and the pixel scale has Nyquist
frequency well below the physicalkmax . To render images
with acceptable speed it is often necessary to approximate the

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    Fourier transform˜I(k) as being identically zero beyond a cho-
sen kmax . This is called band-limiting the image. Common
idealizations of PSFs, such as the Gaussian, Moffat, and Kol-
mogorov functions, are unbounded ink, and therefore we must
select akmax which yields an acceptable approximation.
Every kind of surface brightness proﬁle in GAL SIM is able
to calculate and return itskmax , which we take to be the value
ofk where the Fourier-domain proﬁle drops below a threshold
of 10−3 of the peak. See §6.4 for more detail about the param-
eter (maxk_threshold) that controls this value. For some
proﬁleskmax can be calculated analytically; where this is not
possiblekmax is determined numerically using an appropriate
method for each proﬁle.
Another characteristic of the DFT is that each output value
Ii j= I(i∆x, j∆x) is actually the true function folded at the pe-
riodP = M ∆x = 2π/∆k:
Ii j=
∑
p,q
I(i∆x + pP, j∆x +qP ). (47)
Since it is impossible forI(x) to be compact after being band-
limited, this leads to some degree of inaccuracy due to folding
of the image. We can limit the aliasing errors by ensuring that
every DFT is done with a sufﬁciently large period. Every sur-
face brightness proﬁle in GAL SIM also knows whatkstepvalue
should be used for the DFT (cf.folding_thresholdin
§6.4). The DFT is executed with periodP ≥ 2π/kstep, implying
∆k ≤ kstepand M ≥ 1/kstep∆x.
If the user has requested rendering of an image that does not
meet this criterion, GAL SIM will execute the DFT on a grid of
largerM that does, and then extract the output image from the
result of this larger DFT. If the user does not specify an image
size, GAL SIM will select a value that satisﬁes this bound.
The DFT image must have dimensionM ≥ 2kmax /kstep. Some
of the GAL SIM proﬁles contain sharp features that cause this
minimum M to exceed the maximum allowed DFT size, in par-
ticular thePixelclass and theSersicclass with higher in-
dices, including theDeVaucouleursclass. GAL SIM will
raise an error if one attempts to render such an object via DFT

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    without ﬁrst convolving by another object that attenuates the
high-frequency information. This should not be an issue for
rendering of realistic images, in which convolution with the
14
PSF and pixel response will typically limit the bandwidth of
the image to a manageable value.
6.2.2. Analytic objects
Table 3 lists the proﬁles for which GAL SIM calculates
Fourier-domain values analytically.
For those radial proﬁles without fast analytic formulae in
Fourier domain, we tabulate numerical transforms into a lookup
table and use cubic spline interpolation to return˜I(k). The ini-
tial setup of these tables can take some time, but they are cached
so that later Fourier-domain evaluations of the same type ofpro-
ﬁle are accomplished in constant time.
At small values ofk = |k| we generally replace the spline
interpolation with an analytic quadratic (or higher) orderTay-
lor expansion of˜I(k), because the behaviour of˜I(k) near the
origin has a strong effect on the appearance of poorly-resolved
objects. In particular the second derivative of˜I(k) determines
the second central moments that are critical for measurement
of weak gravitational lensing, and the spline interpolation can
produce incorrect derivatives at the origin.
6.2.3. Shapelet proﬁles
Since shapelets are their own Fourier transforms (cf. equa-
tion (24)), the code to draw aShapeletobject in Fourier
space is essentially identical to the code to directly render it. It
uses fast recurrence relations, which are efﬁcient when applied
to the pixels in the Fourier image.
6.2.4. Interpolated images
Given anN ×N array of samples at pitch∆x, we can perform
a DFT to yield samples of the Fourier transform at a grid of val-
ues ki j= (i/N ∆x, j/N ∆x). To render this function back onto a
differentx-domain grid, or to execute transformations, we need
to evaluate˜I(k) at arbitraryk between the grid of DFT values.
This requires somek-space interpolation scheme.
Furthermore we need to account for the facts that (a) the in-
terpolated image is ﬁnite in extent, while the DFT will yieldthe

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    transform of a periodic function, and (b) it represents a contin-
uous, interpolated version of the input sample grid. Thus two
distinct interpolants are required: thex-domain interpolantK x
is chosen by the user and is part of the deﬁnition ofI(x); thek-
domain interpolantK k is used to generate˜I(k) by interpolating
over the DFT of the input image and the Fourier transform of
K x.
Correct evaluation of the interpolated function ink-space is
not trivial. Bernstein & Gruen (2014) present a detailed de-
scription of the steps required, and we summarize their results
here. First, they ﬁnd that the rigorously correct form ofK k is
a sinc function wrapped at the extent of thex → k DFT. Since
this interpolant spans the entire plane, it means that the inter-
polation of˜I(k) to all theM × M points needed for the DFT
requiresN 2 M 2 operations, which can be prohibitively slow. As
a consequence we normally elect to approximate this using a
compact interpolant forK k.
Bernstein & Gruen (2014) demonstrate that the conse-
quences of this interpolation are a slight multiplicative scaling
of the image, plus the generation of 4 “ghost images” displaced
by N ∆x along each axis. They ﬁnd that these artifacts can be
reduced below 0.001 of the input ﬂux by a combination of zero-
padding the input image by 4× in each direction before con-
ducting thex → k DFT, producing a denser set of samples in
k space, and then using a custom-designed, 6-point piecewise
quintic polynomial interpolant forK k. This recipe is the default
for Fourier-domain rendering of theInterpolatedImage
in GAL SIM . Users can override the default 4-fold zero-padding
factor and/or the choice of theQuinticinterpolant when in-
tializing anInterpolatedImageobject.
The value ofkstep for an interpolated image of input sizeN
and pitch∆x would naively be set at 2π/(N ∆x) to reﬂect the
bounded size of the input image. We must recall, however, that
the interpolation of the input image by the kernelK x will ex-
tend the support of the object and slightly lower the desiredkstep

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    (with the sinc interpolant extending the footprint of the image
enormously).
The value ofkmax for a raw sampled image is inﬁnite be-
cause it is composed ofδ functions. However the application
of the interpolantK x to the samples will cause˜I(k) to roll off
yieldingkmax = cπ/∆x, wherec is a constant characteristic to
the chosenK x. In this respect the band-limited sinc interpolant,
withc = 1, is ideal, but the Lanczos interpolants withn = 3–
5 offer much more compact support with 2< c < 3 sufﬁcing
to contain all aliases with amplitude> 0.001. See Table 1 in
Bernstein & Gruen (2014) for the relevant characteristics of the
interpolants.
6.2.5. Transformations
Transformations of functions have well-known correspon-
dents in Fourier domain, which we quickly review here.
A shiftI′(x) = I(x − x0) has Fourier-domain equivalent
˜I′(k)= eik·x0 ˜I(k). A shift leaveskmax and kstepunchanged.
Linear transformations of the plane, such thatI′(x) =
I(A −1x),are equivalent to˜I′(k)=˜I(A T k).We identify the max-
imum and minimum eigenvaluesλ+ and λ− ofA , and set
kmax → λ−1
− kmax (48)
kstep→ λ−1
+ kstep (49)
6.2.6. Compositions
The Fourier transform is linear, so that ifI(x) = aIA (x) +
bIB (x), we also have˜I(k) = a˜IA (k) + b˜IB (k). When we are
dealing with a sum of multiple componentsIi, we set
kmax = max i(kmax ,i) (50)
kstep= mini(kstep,i) (51)
The convolutionI(x) = (IA ◦ IB )(x) is equivalent to˜I(k) =
˜IA (k)˜IB (k). Under a convolution of multiple elements, we set
kmax = mini(kmax ,i) (52)
kstep=







∑
i
k−2
step,i







−1/2
(53)
15
While the propagation of the band limitkmax is rigorously cor-
rect for convolution, the propagation ofkstepin equation (53) is
merely heuristic. It is based on the exact statement that thecen-
tral second moments of objects sum in quadrature under con-
volution. But there is no general rule for the propagation of
the radius enclosing some chosen fraction of the total object
ﬂux, so our heuristic is known to be correct only for Gaussian

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    objects. For strictly compact functions such as aPixel, the
maximum nonzero elementxmax actually adds linearly, not in
quadrature, under convolution. GAL SIM provides the option to
manually increase the size of DFTs if one is worried that the
kstepheuristic will lead to excessive aliasing.
Finally, aDeconvolveoperation applied to some image
IA (x) yields 1/˜IA (k) in the Fourier domain. We leavekmax and
kstep unaltered, because the deconvolved object is usually ill-
deﬁned unless it is later re-convolved with an object that has a
smallerkmax value.
6.3. Photon shooting
“Photon shooting” was used successfully by Bridle et al.
(2009, 2010) and Kitching et al. (2012, 2013) to generate the
simulated images for the GREAT08 and GREAT10 weak lens-
ing challenges. The objects were convolutions of elliptical
Sérsic-proﬁle galaxies with Moffat-proﬁle PSFs. GAL SIM ex-
tends this technique to enable photon shooting for nearly all of
its possible objects, except for deconvolutions.
When we “shoot” a GAL SIM object,N γ photons are created
with weightsw i and positionsxi. The total weight within any
region has an expectation value of the ﬂux in that region, and
the total weights in any two regions are uncorrelated24.
We allow for non-uniform weights primarily so that we can
represent negative values of surface brightness. This is neces-
sary to realize interpolation with kernels that have negative re-
gions (as will any interpolant that approximates band-limited
behaviour), and to correctly render interpolated images that
have negative pixel values, such as might arise from using em-
pirical, noisy galaxy images.
For photon shooting to be possible on a GAL SIM object, it
must be able to reportfpos and fneg, the absolute values of the
ﬂux in regions withI(x) > 0 andI(x) < 0, respectively. When
N γ photons are requested, we draw their positions from the dis-
tribution deﬁned by|I(x)|and then assign weights
w i = fabs
N γ
sign [I(xi)]= fpos + fneg
N γ
sign [I(xi)]. (54)
Shot noise in the fraction of photons that end up in the

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    negative-brightness regions will lead to variations in thetotal
ﬂux of the photons. GAL SIM mostly accounts for this effect
automatically by selecting an appropriate number of photons to
get the noise correct (cf. §6.3.6). However, the partial cancel-
lations between positive- and negative-ﬂux photons means that
24 This will not be true if you turn off the Poisson variation in the total ﬂux,
which is optional but turned on by default, since then the ﬁxed total ﬂux will
lead to some correlation in the pixel values.
the resulting noise will not actually be distributed precisely ac-
cording to a Poisson distribution for the given ﬂux; only the
variance of the noise will be approximately accurate. For ob-
jects constructed purely from positive-ﬂux proﬁles, this effect
is absent, and the noise is indeed Poisson.
We will see below that in some cases,|w i|is allowed to depart
slightly from the constantfabs/N γ value, which also alters the
noise properties slightly.
6.3.1. Analytic objects
Photon shooting a surface-brightness functionI(x) is sim-
plest when there is a known transformation from the unit square
or circle to the plane whose Jacobian determinant is∝ I.
Pixelis the simplest such case, since it is just a scaling of
the unit square.
Many other proﬁles are circularly symmetric functions with
a cumulative radial distribution function
C (r)=
∫r
0 I(r′)r′ dr′
∫∞
0 I(r′)r′ dr′
. (55)
Ifu is a uniform deviate between 0 and 1,C −1(u) will be dis-
tributed asrI(r), the distribution of ﬂux with radius. A second
uniform deviate can determine the azimuthal angle of each pho-
ton.
G AL SIM uses fast analyticC −1(u) functions for theGaus-
sian(e.g. Press et al., 1992) andMoffatclasses.
For the other circularly symmetric proﬁles we use the follow-
ing algorithm to convert a uniform deviate into the radial ﬂux
distribution of|I|. The algorithm is provided with the function
I(r) and with a ﬁnite set of points{R0,R1,R2,..., R M } with the
guarantee that each interval (Ri,Ri+1) contains no sign changes

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    and at most one extremum ofI(r). The absolute ﬂux|fi|in each
annulus is obtained with standard numerical integration tech-
niques.
Note that this algorithm requires a maximum radius, so the
photon shooting rendering requires truncation of unbounded
proﬁles. The fraction of excluded ﬂux due to this truncationis
given by theshoot_accuracyparameter described in §6.4.
The algorithm proceeds as follows:
1. The code ﬁrst inserts additional nodes into theRi series at
the locations of any extrema.
2. The radial intervals are recursively bisected until either
the absolute ﬂux in the interval is small, or the ratio
max|I|/min |I| over the interval is below a chosen thresh-
old.
3. The integralfi of the absolute ﬂux is calculated for each
annular interval along with the probabilitypi = fi/∑
i fi of
a photon being shot into the interval. We can also calcu-
late the cumulative probabilityPi = ∑
j<i pj of the photon
being interior to the annulus.
4. For each photon we draw a uniform deviateu. It is mapped
to a radiusr by ﬁnding the intervalisuch thatPi ≤ u <
Pi+1 and then assigning
r2 = R2
i+ u −Pi
pi
(
R2
i+1 −R2
i
)
. (56)
16
In other words we drawr from a ﬂux distribution that ap-
proximates|I(r)| as a “wedding cake” of constant-valued
annuli.
5. (a) Ifr is in an interval that has a narrow range of bright-
ness variation, we re-weight the photon by a factor equal
to the brightness atr relative to the mean brightness in the
annulus:
w = fabs
N γ
I(r)π
(
R2
i+1 −R2
i
)
fi
. (57)
(b) If the range of variation ofI in the annulus is large,
which can happen when the annulus is near a zero cross-
ing, we implement rejection sampling by drawing an-
other uniform deviateu′, and keeping the photonr if
|I(r)|/max |I| > u′. If the photon is rejected, we use an-
other uniform deviateu to select a new trial radius within
the interval:
r2 = R2
i+u
(
R2
i+1 −R2
i
)
. (58)
The rejection test is repeated, and the process is iterated
until a photon radius is accepted. This photon is given the
nominal weight (54).

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    6. The azimuthal angle of the photon is selected with a uni-
form deviate.
This procedure yieldsN γ photon locations and weights, em-
ploying 2N γ(1+ǫ) uniform deviates andN γ(1+ǫ) evaluations of
I(r), whereǫ is the fraction of photons rejected in step 5b. We
note that the ﬁnite widths of the annuli must be small for the
approximation to be good: the close correspondence of photon
shooting and DFT rendering results in §9.1 demonstrates that
this is achieved in GAL SIM .
In practice we re-order the intervals into a binary tree (see,
e.g., Makinson, 2012) to optimize the selection of an interval
with the initial uniform deviate. With this tree structure the
mean number of operations to select an interval approaches the
optimal−∑pilogpi < logM , whereM is the ﬁnal number of
radius intervals.
The Sersic,Exponential,DeVaucouleurs,Airy,
and Kolmogorovclasses use this interval-based photon
shooting algorithm. The construction of the interval structure
and ﬂux integrals are done only once for theExponential
and DeVaucouleursproﬁles and once for each distinct Sér-
sic indexn forSersicproﬁles or distinct central obscuration
forAiry. These results are cached for use by future instances
of the classes in each case.
6.3.2. Shapelets
Because shapelet proﬁles are not radially symmetric, imple-
menting photon shooting for such objects represents a signif-
icant challenge (although it is far from impossible). As of
G AL SIM version 1.1, we have not attempted to support photon
shooting forShapeletobjects.
6.3.3. Interpolated images
Photon shooting anInterpolatedImageobject requires
two steps: ﬁrst we distribute the photons among the grid points
(i∆x, j∆x) with probabilitiespi j= |ai j|/∑|ai j|. We select an
ordering for these probabilities and create the cumulativeprob-
abilitiesPi j. For each photon, we draw a uniform deviateu, and
assign an (i, j) value as the last one in the ordering withPi j<u.
The weight is given the sign ofai j. As we did with the radial
function intervals above, we create a tree structure which re-

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    duces the selection of each (i, j) toO (logN ) for anN ×N input
image.
The second step in photon shooting theInterpolated-
Imageis to convolve the gridded samples with the interpola-
tion kernelK x by adding to each photon’s location a displace-
ment drawn from the kernel. Since our 2D interpolants are all
separable into 1D functions, we can draw anx and y displace-
ment from the 1D functions. Theδ-function interpolant can
of course skip this step, and the nearest-neighbour and linear
interpolants are trivially generated from uniform deviates. Pho-
ton shooting is implemented for the other interpolants using the
same algorithm described for the radial analytic functions, with
the replacement ofr2 → x in equations (56) & (57) because of
the linear instead of circular geometry.
Attempts to shoot photons through an image with a sinc in-
terpolant will throw an exception. The long oscillating tail of
the sinc function means thatfabs is divergent.
Photon shooting anInterpolatedImagethus requires
3N γ(1+ǫ) random deviates plus, for most interpolants, 2N γ(1+
ǫ) evaluations of the 1D kernel function.
6.3.4. Transformations
All the transformations described in §3.4 are very simply im-
plemented in photon shooting. Flux rescaling is simply a rescal-
ing of thew i. Any transformation of the plane can be executed
by xi → T (xi).
6.3.5. Compositions
To shootN γ photons from a sum ofM proﬁles, we draw
the number of photons per summand{n1,n2,..., nM } from
a multinomial distribution with expectation value⟨nj⟩ =
N γfabs,j/∑
j fabs,j. Then we concatenate the lists ofni photons
generated by shooting the individual summands.
Convolution is similarly straightforward: to shootN γ pho-
tons throughIA ◦ IB , we drawN γ photons each fromIA and IB ,
set the output weights tow i = w i,A w i,B , and sum the positions to
getxi = xi,A +xi,B .To ensure that there is no correlation between
the photon positions ofA and B in the sequence, GAL SIM ran-
domizes the order of theB photons. This procedure generalizes

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    straightforwardly to the case of convolving more than two pro-
ﬁles together.
We are not aware of a practical means of implementing de-
convolution via photon shooting, so GAL SIM cannot use pho-
ton shooting for any proﬁle that involves a deconvolution.
6.3.6. Selecting an appropriate number of photons
One of the main advantages of using the photon-shooting
method for rendering images is that for objects with low signal-
to-noise (S/N ), it can be much faster to shoot a relatively
small number of photons compared to performing one or more
Fourier transforms. However, for this to be effective, one must
17
know how many photons to shoot so as to achieve the desired
ﬁnalS/N value.
The simplest case is when there are no components that re-
quire negative-ﬂux photons. Then the ﬂuxf of the object given
in photons25 is exactly equal to the number of photons that
would be detected by the CCD. In such a case, the ﬂux itself
provides the number of photons to shoot.
This simple procedure is complicated by a number of con-
siderations. The ﬁrst is that the ﬂux itself is a random variable.
So by default, GAL SIM will vary the total number of photons
according to Poisson statistics, which is the natural behaviour
for real photons. This means that the actual realized ﬂux of the
object varies according to a Poisson distribution with the given
mean value. This feature can also be turned off if desired, since
for simulations, users may want a speciﬁc ﬂux value, rather than
just something with the right expectation value.
A more serious complication happens when there are com-
ponents that require negative-ﬂux photons to be shot, such as
those involving interpolants (cf. §6.3.3). We need more pho-
tons to get the right total ﬂux, since some of them have negative
ﬂux, but then the increased count leads to more noise than we
want. The solution we adopt to address this is to have each
photon carry somewhat less ﬂux and use even more photons.
Let us deﬁneηto be the fraction of photons being shot that

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    have negative ﬂux, and let each photon carry a ﬂux of±g. We
want both the total ﬂux shot and its variance to equal the desired
ﬂux, f:
f = N photons(1−2η)g (59)
Var(f)= N photonsg2 (60)
Setting these equal, we obtain
g = 1 −2η (61)
N photons = f/(1−2η)2 (62)
G AL SIM ’s functiondrawImageautomatically does the
above calculation by default when photon shooting, although
users can override it and set a different number of photons tobe
shot if they prefer.
Note that the above calculation assumes thatη is a constant
over the extent of the proﬁle being shot. In reality, it is notcon-
stant, which leads to correlations between different regions of a
photon-shot image using photons of mixed sign. The resulting
noise pattern will roughly resemble the noise of a real photon
image, but one should not rely on the noise being either sta-
tionary or uncorrelated in this case. Nor will the noise in any
pixel follow Poisson statistics. These inaccuracies gets more
pronounced asηnears 0.5.
There is one additional feature, which can be useful for ob-
jects with moderately high ﬂux, but which are still dominated
25 Technically, in GAL SIM the ﬂux is deﬁned in so-called analog-to-digital
units, ADU. These are the units of the numbers on astronomical images. We
allow againparameter, given in photons/ADU, to convert between these units
and the actual number of photons, combining both the normal gain in e-/ADU
and the quantum efﬁciency in e-/photon. The default behaviour is to ignore all
these issues and use a gain of 1.
by sky background light (a relatively common use case). It may
take many photons to get the noise level correct, a computa-
tional cost which is wasted if a larger amount of noise is then
added from the sky background. The same ﬁnalS/N can be ob-
tained (to a very good approximation) by shooting fewer pho-
tons, each with ﬂux larger than the normal choice ofg = 1 −2η.
To address this, GAL SIM has an option to allow the pho-
ton shooting process to add an additional noise per pixel over

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    the Poisson noise expected for each pixel. Each pixel may be
allowed to haveν excess variance. The brightest pixel in the
image, with ﬂuxImax , can then have a variance of up toImax +ν.
Thus the number of photons can be reduced by as much as
Imax /(Imax + ν). The ﬂux carried by each photon is increased
to keep the total ﬂux equal to the target value,f:
N photons ≥ Imax f
(Imax +ν)(1−2η)2 (63)
g = f
N photons(1−2η) (64)
Clearly, this is only helpful ifν≫ Imax , which is indeed the case
when the image is sky noise dominated. This is a common use
case in realistic simulations, particularly ones that are meant to
simulate ground-based observations.
Users of this behaviour in GAL SIM must explicitly indicate
how much extra noise per pixel,ν, is tolerable. Typically this
will be something like 1% of the sky noise per pixel. This isnot
the default behaviour, because at the time of rendering the im-
age, the code does not know how much (or whether) sky noise
will be added.
An additional complication with the above prescription is
that the code does not know the value ofImax a priori. So the ac-
tual algorithm starts by shooting enough photons to get a decent
estimate forImax . Then it continues shooting until it reaches the
value given by equation (63), while periodically updating the
estimatedImax . At the end of this process, it rescales the ﬂux of
all the photons according to equation (64) using the ﬁnal value
ofN photons.
6.4. Setting tolerances on rendering accuracy
Some of the algorithms involved in rendering images involve
tradeoffs between speed and accuracy. In general, we have
set accuracy targets appropriate for the weak lensing require-
ments of Stage IV surveys such as LSST,Euclid(Laureijs et al.,
2011), andWFIRST (cf. §9). However, users may prefer faster
code that is slightly less accurate for some purposes, or more ac-
curate but slower for others. This is possible in GAL SIM using
a structure calledGSParams, which includes many parameters
pertaining to the speed versus accuracy tradeoff, some of which

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    are described below:
• folding_threshold26 sets a maximum permitted
amount of real space image folding due to the periodic
26In earlier versions of G AL SIM this parameter was named
alias_threshold. It was renamed for clarity and to avoid confusion with
the phenomenon of aliasing in undersampled data.
18
nature of DFTs, as described in §6.2.1. It is the critical pa-
rameter for deﬁning the appropriate step sizekstep. Addi-
tionally, it is relevant when letting GAL SIM choose output
image sizes: the image will be large enough that at most a
fractionfolding_thresholdof the total ﬂux falls off
the edge of the image. The default is5.e-3.
• maxk_thresholdsets the maximum amplitude of the
high frequency modes in Fourier space that are ex-
cluded by truncating the DFT at some maximum value
kmax . As described in §6.2.1, this truncation is required
for proﬁles that are not formally band-limited. Reduc-
ingmaxk_thresholdcan help minimize the effect of
“ringing” in images for which this consideration applies.
The default is1.e-3.
• xvalue_accuracyand kvalue_accuracyset the
accuracies of values in real and Fourier space respectively.
When an approximation must be made for some calcula-
tion, such as when to transition to Taylor approximation as
smallr ork, the error in the approximation is constrained
to be no more than one of these values times the total ﬂux.
The default for each is1.e-5.
• realspace_relerrand realspace_abserrset
the relative and absolute error tolerances for real-space
convolution. The estimated integration error for the ﬂux
value in each pixel is constrained to be less than ei-
therrealspace_relerrtimes its own ﬂux orre-
alspace_abserrtimes the object’s total ﬂux. The de-
fault values are1.e-4and 1.e-6respectively.
• shoot_accuracysets the relative accuracy on the
total ﬂux when photon shooting. When the photon-
shooting algorithm needs to make approximations, such
as how high in radius it must sample the radial pro-
ﬁle, the resulting fractional error in the ﬂux is limited to

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    shoot_accuracy. The default value is1.e-5.
There are several less important parameters that can also be
set similarly, but the above parameters are the most relevant for
most use cases. All the GAL SIM objects described in §3 have
an optional parametergsparamsthat can set any number of
these parameters to a non-default value when initializing the
object.
6.5. Representing realistic galaxies
G AL SIM can carry out a process (‘reconvolution’) to render
an image of a real galaxy observed at high resolution (with the
HST ),removing theHST PSF, with an applied lensing shear
and/or magniﬁcation, as it would be observed with a lower-
resolution telescope. Reconvolution was mentioned in Kaiser
(2000) and implemented in Mandelbaum et al. (2012) in the
SHERA (SHEar Reconvolution Analysis) software27.
27http://www.astro.princeton.edu/~rmandelb/shera/
shera.html
Reconvolution is possible when the target band limitkmax,targ
relates to the originalHST band limitkmax,HST via
kmax,targ<
(
1 −
√
κ2 +γ2
)
kmax,HST . (65)
For weak shears and convergences, this condition is easily sat-
isﬁed by all upcoming lensing surveys, even those from space.
In GAL SIM , theRealGalaxyclass represents theHST
galaxy deconvolved by its original PSF. This can then be trans-
formed (sheared, etc.) and convolved by whatever ﬁnal PSF is
desired. Observations of galaxies from theHST COSMOS sur-
vey (described in Koekemoer et al., 2007), which form the basis
of theRealGalaxyclass, are available for download from the
G AL SIM repository28. Padding the input postage stamp images
is necessary, for the reasons described in §6.2.4. We carry out
noise padding on the ﬂy, with a noise ﬁeld corresponding to that
in the rest of the postage stamp (unlikeSHERA , which required
padded images as inputs). The amount of padding was exten-
sively tested during the numerical validation of the GAL SIM
software, and results for the default (strongly recommended)
choice are described in §9.2.
The implementation is updated compared to that inSHERA

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    in several ways. First,SHERA only implemented a cubic inter-
polant, whereas GAL SIM includes many interpolants that can
be tuned to users’ needs (c.f. §3.3.3). Second, GAL SIM fully
deconvolves the originalHST PSF. SHERA uses a technique
called pseudo-deconvolution, only deconvolving theHST PSF
on scales accessible in the ﬁnal low-resolution image. In prac-
tice, the difference between pseudo-deconvolution and decon-
volution is irrelevant, and what matters is the ability to render
sheared galaxies very accurately (see §9). Finally, the original
HST images typically contain correlated noise, and further cor-
relations are introduced by the shearing and subsequent convo-
lution. In §7.5 we describe how GAL SIM (unlikeSHERA ) can
model this correlated noise throughout the reconvolution pro-
cess and then whiten the ﬁnal rendered image so that it contains
only uncorrelated Gaussian noise.
7. Noise models
Noise is a feature of all real imaging data, due to ﬁnite num-
bers of photons arriving at each detector, thermal noise and
electronic noise within the detector and readout, and otherlossy
processes. GAL SIM therefore provides a number of stochastic
noise models that can be applied to simulated images.
It is worth noting that images rendered by photon shooting
(see §6.3) already contain noise: photon counts are drawn from
a Poisson distribution of mean equal to the expected ﬂux at each
pixel. But there may still be occasions when it is desirable to
add further noise, such as to simulate a shallower image or to
add detector read noise. Images rendered by DFT (§6.2) need
noise to be added to be made realistic.
28https://github.com/GalSim-developers/GalSim/
wiki/RealGalaxy%20Data
19
7.1. Random deviates
Underlying all the noise models in GAL SIM are implementa-
tions of random deviates that sample from a range of probability
distributions. These include the uniform distributionU(0,1)
(implemented by theUniformDeviateclass), the Gaus-
sian/normal distributionN(µ,σ2) (GaussianDeviate), and

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    the Poisson distribution Pois(λ) (PoissonDeviate).
These fundamentally important distributions form the basis
of noise models in GAL SIM , but they are also quite useful for
generating random variates for various galaxy or PSF parame-
ters in large simulations. Additionally, we include some other
distributions that are more useful in this latter context rather
than for noise models: the binomial distribution, the Gamma
distribution, the Weibull distribution (a generalizationof the
exponential and Rayleigh distributions) and theχ2 distribution
(see, e.g., Johnson et al., 2005).
Finally, GAL SIM also supports sampling from an arbitrary
probability distribution function, supplied by the user inthe
form of either a lookup table and interpolating function, ora
callable Python function with a speciﬁed min and max value
range. This is the implemented by theDistDeviateclass.
7.2. Uncorrelated noise models
The majority of noise models that GAL SIM implements gen-
erate uncorrelated noise, i.e. noise that takes a statistically inde-
pendent value from pixel to pixel. The simplest is theGaus-
sianNoiseclass, which adds values drawn fromN(0,σ2) to
an image. The noise is thus spatially stationary, i.e. having a
constant variance throughout the image, as well as being uncor-
related.
The PoissonNoiseclass adds Poisson noise Pois(λi) to
thei-th pixel of the image, whereλi corresponds to the mean
number of counts in that pixel (an optional sky level can be
supplied when simulating sky-subtracted images). ThePois-
sonNoisemodel is not stationary, since the variance varies
across the image according to the different pixel ﬂuxes.
The CCDNoiseclass provides a good approximation to the
noise found in normal CCD images. The noise model has two
components: Poisson noise corresponding to the expected pho-
ton countsλi in each pixel (again with optional extra sky level)
and stationary Gaussian read noiseN(0,σ2). It is also possi-
ble to specify a gain value in photons/ADU (analog-to-digital

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    units)29, in which case the Poisson noise applies to the photon
counts, but the image gets values in ADU.
The VariableGaussianNoiseclass implements a non-
stationary Gaussian noise model, adding noise drawn from
N(0,σ2
i), using a different variance for each pixeliin the im-
age.
Finally, any random deviate from §7.1 can be used as the
basis for a simple GAL SIM noise model, using theDevi-
ateNoiseclass, which draws from the supplied random de-
viate independently for each pixel to add noise to the image.
29 Normally the gain is given in e-/ADU, but in GAL SIM we combine the
effect of the gain with the quantum efﬁciency, given in e-/photon
7.3. Correlated noise
Astronomical images may contain noise that is spatially cor-
related. This can occur at low levels due to detector crosstalk
(e.g. Moore et al., 2004; Antilogus et al., 2014) or the use of
pixel-based corrections for charge transfer inefﬁciency (CTI,
Massey et al. 2010), and it can be strikingly seen in images
that have been created through the coaddition of two or more
dithered input images.
Drizzled HST images (Fruchter & Hook, 2002;
Koekemoer et al., 2003) often have correlated noise due
to the assignment of ﬂux from single input pixels to more
than one output pixel. The drizzledHST COSMOS survey
images (see Koekemoer et al., 2007) used as the basis for
empirical galaxy models described in §6.5 contain signiﬁcant
inter-pixel noise correlations. For faint objects, such asthe
galaxies typically of interest for weak lensing, such noiseis
well approximated as a set of correlated Gaussian random
variables.
7.3.1. Statistics of correlated Gaussian noise
The statistical properties of correlated Gaussian noise are
fully described by a covariance matrix. If we denote a noise
ﬁeld asη, we may deﬁne a discrete pixel-noise autocorrelation
function
ξnoise[n,m ]= ⟨η[i, j]η[i′, j′]⟩
i′−i=n, j′−j=m , (66)
where the angle brackets indicate the average over all pairsof
pixel locations [i, j] and [i′, j′] for whichi′−i= n and j′−j= m .

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    (Here we use square brackets for functions with discrete, inte-
ger input variables.) Thereforen,m denote the integer separa-
tion between pixels in the positivex and y directions, respec-
tively. All physicalξnoise[n,m ] functions have two-fold rota-
tional symmetry, so thatξnoise[−n,−m ] = ξnoise[n,m ], and are
peaked atn = m = 0. If the noise is stationary, i.e. its variance
and covariances do not depend upon location in the image, then
ξnoise[n,m ] fully determines the covariance matrix for all pairs
of pixels in an image.
For any physical, discrete pixel-noise correlation function
ξnoise[n,m ] there is a positive, real-valued noise power spectrum
Pnoise[p,q] that is its Fourier counterpart (i.e. the two are related
by a DFT). We usep,q to label array locations in Fourier space,
and n,m in real space.
The functionPnoise[p,q] can be used to generate random
noise as a Gaussian ﬁeld. We may construct an array˜η[p,q]
as
˜η[p,q]=
√
Pnoise[p,q]N
2 {N(0,1)+iN(0,1)} (67)
where samples from the standard Gaussian distributionN(0,1)
are drawn independently at each locationp, q (subject to the
condition that˜η[p,q] is Hermitian, see below), andN is the to-
tal array dimension in either direction (we assume square arrays
for simplicity). The inverse DFT, as deﬁned in equation (A.17),
is then applied to generate a real-valued noise ﬁeld realization
in real spaceη[n,m ]. The enforced Hermitian symmetry of
˜η[p,q] is exploited to enable the use of efﬁcient inverse-real
DFT algorithms. It can be seen that the resultantη[n,m ] will
have the required discrete correlation functionξnoise[n,m ].
20
7.3.2. Representing correlated Gaussian noise
Stationary correlated noise is modelled and generated in
G AL SIM by theCorrelatedNoiseclass. Internally the
noise correlation functionξnoise[n,m ] is represented as a 2D
distribution using the same routines used to describe astro-
nomical objects, described in §3. Using these to calculate
the noise power spectrum, and then applying the expression in

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    equation (67) followed by an inverse DFT, theCorrelat-
edNoiseclass can be used to generate a Gaussian random
ﬁeld realization with any physical power spectrum or correla-
tion function.
Because theCorrelatedNoiseclass internally uses a
regular GAL SIM surface brightness proﬁle to describe the cor-
relation function, it is easy to effect the transformation,as in
§3.4, since the noise is transformed in the same manner. Simi-
larly, multiple noise ﬁelds may be summed (as will be required
in §7.5), since the resultantξnoise is given by the sum of the
individual noise correlation functions.
The effect of convolution of a noise model by some kernel
is not quite the same as what happens to surface brightness.
Instead,ξnoiseshould be convolved by the autocorrelation of the
kernel. The ability to describe transformations, combinations
and convolutions of noise is valuable, as will be discussed in
§7.5.
7.3.3. Describing discrete correlation functions inR2
The description of the discrete correlation function
ξnoise[n,m ] as a distribution inR2 is worthy of some discus-
sion. As will be seen in §7.5 it is important to be able to take
into account the ﬁnite size of pixels in images that may con-
tain correlated noise, particularly when these images are being
used to form galaxy models that will ultimately be rendered
onto a pixel grid of a different scale. We therefore wish to rep-
resentξnoise[n,m ] as a function of continuous spatial variables,
ξnoise(x,y) for which we require
ξnoise(ns,ms )= ξnoise[n,m ], (68)
where s is the pixel scale.
Let us consider an image containing noise. In the absence of
any smoothing of the image, it is described mathematically as
an array of delta function samples (located at the pixel centres)
convolved by the pixel response. This could also be considered
the formally correct model to use forξnoise(x,y): its values, like
those in an image, should change discontinuously across the
boundaries between pixels as separation increases continuously.
However, this description ofξnoise(x,y) presents difﬁculties

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    when performing certain of the operations described in §7.3.2,
e.g. convolutions, or transformations followed by a convolution.
The presence of sharp discontinuities at every pixel-associated
boundary makes the necessary Fourier space representationof
ξnoise(x,y) extremely non-compact, and prohibitive in terms of
memory and computing resources.
Therefore, to reduce the computational costs of handling
Gaussian correlated noise to tolerable levels, GAL SIM adopts
bilinear interpolation between the sampled valuesξnoise(ns,ms )
to deﬁne the continuous-valued functionξnoise(x,y) within the
CorrelatedNoiseclass.
−5 0 5
∆x [pixels]
−5
0
5
∆y [pixels]
COSMOS F814W ACS-WFC log10[|ξnoise|/max|ξnoise|]
−3.2
−2.8
−2.4
−2.0
−1.6
−1.2
−0.8
−0.4
0.0
Figure 1: Illustration of the GAL SIM estimate of the discrete pixel noise cor-
relation functionξnoise in the 0.03 arcsec/pixel, unrotated COSMOS F814W
science images of Leauthaud et al. (2007), made by averagingestimates from
blank sky ﬁelds as described in §7.4. The plot depicts the logof the corre-
lation function normalized so thatξnoise[0,0] = 1 for clarity, and shows only
the central region corresponding to small separations∆x,∆y, which dominate
covariances.
In practice, the impact of this efﬁciency-driven approxima-
tion may often be small. The primary use case for the rep-
resentation of correlated noise within GAL SIM is in handling
noise in models derived from direct observations of galaxies
(see §6.5 and §7.5). In these applications, both the appliedPSF
and the pixel scale on which the ﬁnal image will be rendered
are typically signiﬁcantly larger than the pixel scale of the in-
put images. The use of bilinear interpolation represents a small
additional convolution kernel in these cases.
7.4. COSMOS noise
The HST COSMOS galaxy images made available for
download with G AL SIM for use in the RealGalaxy
class (see Koekemoer et al., 2007; Leauthaud et al., 2007;
Mandelbaum et al., 2012) contain noise that is spatially cor-
related due to drizzling. To construct a model for this cor-

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    related noise, we estimated the discrete pixel noise correla-
tion function in∼100 rectangular regions selected from empty
sky in the public, unrotated, ACS-WFC F814W science im-
ages (0.03 arcsec/pixel) from COSMOS (described in detail by
Koekemoer et al., 2007; Leauthaud et al., 2007).
Each rectangular region varied in size and dimensions, being
chosen so as not to include any detected objects, but were typ-
ically square regions∼50-200 pixels along a side. The mean
noise correlation function in these images (calculated by sum-
ming over each individual estimate, see §7.3.2) provides an
estimate of the mean noise correlation function in COSMOS
F814W galaxy images used by GAL SIM as the basis for galaxy
models. The resulting estimate ofξnoiseis depicted in Fig. 1.
This model is included with the GAL SIM software for gen-
eral use in handling images that contain noise like those in the
COSMOS F814W images, and is accessible via thegetCOS-
MOSNoise()convenience function.
21
7.5. Noise whitening
All images of galaxies from telescope observations will con-
tain noise. As pointed out by Mandelbaum et al. (2012), this
noise will become sheared and correlated (in an anisotropic
way) by the action of the reconvolution algorithm describedin
§6.5, which can result in a signiﬁcant systematic offset in the re-
sults from galaxy shear simulations. Mandelbaum et al. (2012)
found that the presence of correlated noise caused∼1% level er-
rors in the determination of calibration biases for weak lensing
shear for high-S/N galaxies; the effect is worse at lowerS/N ,
and cannot be ignored for high-precision shear simulations.
G AL SIM addresses the presence of correlated noise in sim-
ulated images, such as the sheared, convolved noise ﬁelds cre-
ated by the reconvolution algorithm, through a process referred
to as “noise whitening”. This technique adds further noise to
images, with a correlation function chosen to make the combi-
nation of the two noise ﬁelds approximately uncorrelated and

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    stationary (aka “white”).
We consider an image containing correlated Gaussian noise
that we label asη. We assume⟨η⟩= 0 and we modelηas sta-
tionary across the image so that its covariance matrix is fully
described by its correlation functionξnoise[n,m ] or power spec-
trum Pnoise[p,q]. We add additional whitening noise which we
labelηwhitening, giving a combined noise ﬁeld
ηtotal= η+ηwhitening. (69)
The statistics ofηwhiteningare also determined by its power spec-
trum,Pwhitening[p,q], andηwhiteningwill be physically realizable
provided that
Pwhitening[p,q]≥ 0 (70)
for allp,q. The power spectrum of the combined noise ﬁeld is
simply
Ptotal= Pnoise+ Pwhitening. (71)
We may choose Pwhiteningso thatηtotalis uncorrelated by re-
quiringPtotalto be a constant (a ﬂat power spectrum corre-
sponds to a delta function correlation function, which is white
noise). This, and the requirementPwhitening≥ 0, is satisﬁed by
choosing
Pwhitening[p,q]= max
p,q
{Pnoise[p,q]}− Pnoise[p,q]. (72)
In practice, GAL SIM adds a small amount of additional vari-
ance so thatPwhitening>0, deﬁning
Pwhitening[p,q]= (1+ǫ)×max
p,q
{Pnoise[p,q]}
−Pnoise[p,q] (73)
where ǫ = 0.05 by default. The whitening noiseηwhiteningcan
then be added following the prescription described in §7.3.1,
using the expression forPwhiteningabove. At a relatively small
fractional cost in additional variance, the ‘headroom’ parameter
ǫ effectively guaranteesPwhitening[p,q] ≥ 0. Withoutǫ this im-
portant condition might not be met, due to numerical rounding
and approximations in the description ofξ[n,m ] (see §7.3.3).
−3 −2 −1 0 1 2 3
Separation ∆x [pixel]
10-5
10-4
10-3
10-2
10-1
100
|ξnoise| / max|ξnoise|
COSMOS noise
−3 −2 −1 0 1 2 3
Separation ∆x [pixel]
10-5
10-4
10-3
10-2
10-1
100
Whitened noise
−3 −2 −1 0 1 2 3
Separation ∆y [pixel]
10-5
10-4
10-3
10-2
10-1
100
|ξnoise| / max|ξnoise|
−3 −2 −1 0 1 2 3
Separation ∆y [pixel]
10-5
10-4
10-3
10-2
10-1
100
Figure 2: Left panels: cross section through the discrete pixel noise correlation

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    functionξnoisefor the COSMOS F814W blank sky ﬁelds described in §7.4 and
shown in Fig. 1, normalized to unit zero-lag variance; the upper left panel shows
COSMOS noise correlations in the direction∆y = 0, and the lower left panel
shows COSMOS noise correlations in the direction∆x = 0. Right panels: cross
section through the normalized discrete pixel noise correlation functions for a
single∼400 pixel× 300 pixel patch of blank sky, taken from COSMOS, to
which further whitening noise has been added using the §7.4 model forξnoise,
using the procedure described in §7.5. As for the left panels, the upper right and
lower right panels show correlations along the directions∆y = 0 and∆x = 0,
respectively. Unﬁlled bars represent negative correlation function values.
Fig. 2 shows cross sections throughξtotal[n,m ] from a sin-
gle∼ 400 × 300 pixel patch of blank sky taken from COS-
MOS F814W ACS-WFC images, to which further whitening
noise has been added.Pwhiteningwas calculated using the model
forξnoise (and thusPnoise) described in §7.4 along with equa-
tion (73). Here GAL SIM noise whitening has lowered inter-
pixel covariances to∼10−2–10−3 of the zero-lag variance in the
whitened image.
We have tested that applying this whitening procedure to
COSMOS noise ﬁelds that have been sheared and convolved
(like those produced by the reconvolution algorithm of §6.5)
similarly reduce the noise correlations by 2–3 orders of mag-
nitude, making them statistically undetectable in all but the
largest simulated images.
The price paid for noise whitening is additional variance in
the output image. The noise added in equation (69) is an ad-
ditional stochastic degradation of an image. For the COSMOS
F814W noise ﬁeld whitened in Fig. 2, the ﬁnal noise ﬁeld there-
fore has a variance that is greater than the variance in the orig-
inal images. However, the correlated noise in a COSMOS im-
age itself results in a lower effectiveS/N for estimates of ob-
ject properties such as ﬂux, or shape, relative to the case ofan

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    image with the same variance but with pure white noise (for
a discussion of these effects, which depend on object size and
the properties of the correlated noise, see, e.g., Casertano et al.,
2000; Leauthaud et al., 2007). The effect of additional whiten-
ing of the noise in such an image, therefore, reduces theS/N
of estimates of object properties by less than implied by thera-
22
tio of pre- and post-whitening image variances. The amount
of information lost in whitening will depend on the property
in question, the object proﬁle, and the noise correlations in the
original image.
In the case of noise ﬁelds that have been sheared, convolved
by a PSF, and then rendered on an image with a larger pixel
scale (as described in §6.5), the noise added in whitening de-
pends not only on the original noise correlation function, but
also on the applied shear, PSF, and ﬁnal pixel scale. Interest-
ingly, it is found to be typically substantially lower in overall
variance than in the case of whitening raw COSMOS noise
at native resolution (the case described above and shown in
Fig. 2).
On investigation, this was found to be due to a combina-
tion of effects. The shear and convolution both increase the
noise correlations at large scales. However, the ﬁnal image
rendering typically has a pixel scales signiﬁcantly larger than
the 0.03 arcsec/pixel of the COSMOS images, which means
that the values of the correlation function at integer multiples
of s in separation are often smaller than in the original COS-
MOS image. Also, convolution with a broad PSF reduces the
overall noise variance considerably, being essentially a smooth-
ing kernel. These effects combine fortuitously in practice:
Mandelbaum et al. (2014) found that only a relatively modest
amount of whitening noise is required to treat the sheared, cor-
related noise in images generated by the reconvolution algo-
rithm of §6.5 with a ground-based target PSF and pixel scale.
In GAL SIM theImageclass has a methodwhitenNoise
that applies the above whitening algorithm to a given im-

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    age. This method also returns the theoretical estimate of
the noise variance in the ﬁnal whitened image (namely (1+
ǫ) maxp,q {Pnoise[p,q]}). In addition, there is a methodsym-
metrizeNoisethat imposesN -fold symmetry (for evenN ≥
4) on the noise ﬁeld rather than making it entirely white. Typ-
ically far less noise must be added bysymmetrizeNoise
compared towhitenNoise, which makes it a useful option
for those applications that do not require fully white noise.
The RealGalaxyclass has an attributenoisethat keeps
track of the estimated correlated noise in the proﬁle. When this
object is transformed or convolved, the new object will also
have anoiseattribute that has had the appropriate transforma-
tion done to propagate the noise in the new proﬁle. This allows
G AL SIM to automatically track the effect of transformations on
noise ﬁelds without much user input required. The ﬁnal pro-
ﬁle’snoiseattribute can then be used to whiten the rendered
image. Furthermore, users can add anoiseattribute them-
selves to any object they create and get the same behaviour.
In a larger image with many scattered, possibly overlapping
galaxies, the correlated noise in the original images may differ,
further complicating the task of getting uniform white noise in
the ﬁnal image. GAL SIM handles this by drawing each galaxy
on its own postage stamp image and whitening that individu-
ally. Still, the ﬁnal image has a complicated patchwork of noise
with different regions having different variances, but it is rela-
tively straightforward in GAL SIM to keep track of these noise
levels: the conﬁguration ﬁle interface described in §2.3 allows
this to be handled automatically. Then theVariableGaus-
sianNoiseclass can add a variable amount of noise to each
pixel to bring the noise up to a uniform value across the entire
image.
8. Shear estimation
G AL SIM includes routines for estimation of weighted mo-
ments of galaxy shapes and for estimation of PSF-corrected
shears. The code for these routines was originally introduced

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    by Hirata & Seljak (2003) (hereafter HS03), including an en-
tirely new PSF correction method known as re-Gaussianization.
These routines were later tested, improved, and optimized in
subsequent work (Mandelbaum et al., 2005, 2012; Reyes et al.,
2012). The code was developed as a free-standing C package
namedHSM , and was released publicly under an open source
license simultaneously with its incorporation into GAL SIM .
The functionFindAdaptiveMomentsimplements the
“adaptive moments” method described in §2.1 of HS03, based
on Bernstein & Jarvis (2002). It iteratively computes the mo-
ments of the best-ﬁtting elliptical Gaussian, using the ﬁtted el-
liptical Gaussian as a weight function.
The functionEstimateShearimplements multiple meth-
ods that were tested in HS03:
1. The PSF correction method described in Appendix C of
Bernstein & Jarvis (2002) tries to analytically account for
the effect of the kurtosis of the PSF (in addition to the
second order moments) on the galaxy shapes.
2. The “linear” method (described in Appendix B of HS03) is
a variant of the previous method that accounts for the ﬁrst-
order departure of both the PSF and galaxy from Gaus-
sianity.
3. The “re-Gaussianization” PSF correction method de-
scribed in §2.4 of HS03 models the PSF as a Gaussian
plus a residual, and subtracts from the observed image
an estimate of the residual convolved with the pre-seeing
galaxy. The resulting image has roughly a Gaussian PSF,
for which the methods described above can be used for the
ﬁnal PSF correction.
4. A speciﬁc implementation of the KSB method
(Kaiser et al., 1995; Luppino & Kaiser, 1997), as de-
scribed in Appendix C of HS03, is also provided.
These routines work directly on GAL SIM images. The ﬁrst
three PSF correction methods output a measure of per-galaxy
shape called a distortion, which for an ensemble of galaxies
can be converted to shear estimates via a responsivity factor
(cf. Bernstein & Jarvis 2002). The outputs are clearly labeled
as being distinct from per-galaxy shear estimates, such as those

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    output by the KSB routine.
As is typical for all shape measurement algorithms, there
are several tunable parameters for the above methods and for
moment estimation overall (with adaptive moment estimation
playing a role in all but the KSB method of PSF estimation).
G AL SIM therefore includes two ways of tuning these param-
eters. There is anHSMParamsstructure that allows users to
23
change parameters that affect how the submodule works over-
all. Other parameters are given as arguments to the speciﬁc
functions.
Aside from the obvious utility of being able to operate di-
rectly on images in memory, rather than ﬁles, the versions of
these routines in GAL SIM come with some improvements over
the free-standing C code. These include an intuitive and more
ﬂexible user interface; optimization of convolutions, theexp
function (via reduction of the number of function calls), and
Fourier transforms (using theFFTW package, Frigo & Johnson,
2005); a clean way of including masks within images that is
easily extensible to variable weight maps; and a ﬁx for a bug
that caused the original C code to work incorrectly if the input
PSF images were not square.
9. Numerical validation
In this Section we describe the investigations that were un-
dertaken to validate the accuracy of GAL SIM image simula-
tions. Although an exhaustive validation of the rendering of
every combination of galaxy/PSF proﬁles and observing con-
ditions is impractical, certain key aspects of GAL SIM perfor-
mance are shown here. Emphasis is placed on conﬁrming that
G AL SIM meets the stringent requirements on image transfor-
mations for lensing shear and magniﬁcation simulation.
In particular, our metric for validating that the rendered im-
ages are sufﬁciently accurate is based on measurements of the
size and ellipticity of the rendered proﬁles, calculated using the
adaptive moment routines described in §8.
We deﬁne the following “STEP-like” (see Heymans et al.,
2006) models for the errors in the estimates of object ellipticity

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    g1 and g2 and sizeσ:
∆gi = m igi +ci, (74)
∆σ= m σσ+cσ, (75)
where i = 1,2. The method of estimating the errors∆gi and
∆σvaries for each of the validation tests described below, buta
common component is adaptive moments estimates of rendered
object shapes from images (see §8). We will use the formulae
above when describing the nature of the errors in each test.
As discussed in Mandelbaum et al. (2014), a well-motivated
target for simulations capable of testing weak lensing measure-
ment is to demonstrate consistency at a level well within the
overall requirements for shear estimation systematics setby Eu-
clid(e.g. Cropper et al., 2013; Massey et al., 2013):m i ≃ 2 ×
10−3 and ci ≃ 2 ×10−4. Such values also place conservative re-
quirements on galaxy size estimation, as the signal-to-noise ex-
pected for cosmological magniﬁcation measurements has been
estimated as≲ 50% relative to shear (e.g. van Waerbeke, 2010;
Schmidt et al., 2012; Duncan et al., 2014).
Only if these stringentEuclidconditions are met comfortably
will simulations be widely usable for testing weak lensing shear
estimation, and other precision cosmological applications, in
the mid-term future. For each validation test we therefore re-
quire that GAL SIM can produce images showing discrepancies
that are a factor of 10 or more below theEuclidrequirements,
i.e.m x < 2 × 10−4, cx < 2 × 10−5, wherex = 1,2,σ corre-
sponding tog1,g2 and σ, respectively. Our intention is to show
that rendering accuracy improves with more stringent rendering
parameter settings, and can be raised to meet the requirement
above. GAL SIM default settings for these parameters, however,
are chosen to reﬂect a balance between speed and accuracy for
general use. Although these defaults typically take valuesthat
guarantee meeting 1/10thEuclidrequirements, this is not ex-
clusively the case (see §9.3).
For our tests, we use comparisons of rendering methods us-
ing adaptive moments measurements. Although there are inac-
curacies inherent in such measurements in an individual sense,

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    we take care to construct our comparisons to be sensitive only
to differences in the image rendering. For example, the tests
always compare noise-free orextremelylow noise images, with
the same underlying galaxy model. Noise bias and model bias
therefore affect each test subject in the same way, and differ-
ences are due solely to how the test images were rendered.
The tests in this Section were conducted over a period of ex-
tended validation of the GAL SIM software between July 2013
and the time of writing this paper. During this time period, cor-
responding approximately to versions 1.0 and 1.1 of GAL SIM ,
the routines for rendering objects did not change signiﬁcantly
(except where modiﬁcations were found necessary to meet the
validation criteria onm x and cx deﬁned above).
9.1. Equivalence of DFT rendering and photon shooting
One of the principal advantages of the photon shooting
method (see §6.3) is that the implementations of the various
transformations described in §3.4 are very simple. Photonsare
just moved from their original position to a new position. Con-
volutions are similarly straightforward. On the other hand, DFT
rendering (see §6.2) needs to deal with issues such as band lim-
iting and aliasing due to folding (cf. §6.2.1).
Thus a powerful test of the accuracy of our DFT implementa-
tion is that the the two rendering methods give equivalent results
in terms of measured sizes and shapes of the rendered objects.
An unlikely conspiracy of complementing errors on both sides
would be required for this test to yield false positive results.
Of all the objects in Table 3, Sérsic proﬁles are the most nu-
merically challenging to render using Fourier methods. Espe-
cially forn ≳ 3, the proﬁles are extremely cuspy in the cen-
tre and have very broad wings, which means that they require
a large dynamic range ofk values when performing the DFT.
They therefore provide a good test of our choices for parame-
ters such asfolding_thresholdand maxk_threshold
(see §6.4) as well as general validation of the DFT implemen-

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    tation strategies.
For our test, we builtSersicobjects with Sérsic indices in
the range 1.5 ≤ n ≤ 6.2. The half-light radii and intrinsic el-
lipticities|g(s)|were drawn from a distribution that matches ob-
served COSMOS galaxies, as described in Mandelbaum et al.
(2014). The galaxies were then rotated to a random orienta-
tion, convolved with a COSMOS-like PSF (a circularAiry
proﬁle), and then rendered onto an image via both DFT and
photon shooting.
24
The error estimates were taken to be the difference between
the adaptive moments shape and size estimates from the two
images:
∆gi = gi,DFT −gi,phot (76)
∆σ= σDFT −σphot (77)
For each galaxy model, we made multiple trial photon shoot-
ing images, each with very highS/N to avoid noise biases (107
photons shot per trial image). The mean and standard error of
∆gi and ∆σfrom these trials were used to estimate values and
uncertainties form x,DFT and cx,DFT using standard linear regres-
sion.
Differences between shape and size estimates are illustrated
in Fig. 3, forn = 1.5 andn = 6.2. Fig. 4 shows derived esti-
mates ofm x,DFT for these and other Sérsic indices tested. Toler-
ances are met onm -type biases. It was found thatc-type addi-
tive biases were consistent with zero for alln indices.
Fig. 5 shows results from a high-precision investigation of
m x,DFT as a function ofGSParamsparameters (see §6.4), us-
ing a randomly selected sample of 270 galaxies from COS-
MOS at each parameter value and large numbers of photons.
Each galaxy was generated in an 8-fold ring test conﬁgura-
tion (Nakajima & Bernstein, 2007) to further reduce statistical
uncertainty. The plot in Fig. 5 shows the impact of increas-
ing thefolding_thresholdparameter: as expected, the
rendering agreement decreases asfolding_thresholdin-
creases, and the representation of object size is most affected.
Analogous results were achieved for many of the parameters
discussed in §6.4, and the defaultGSParamsparameters were
found to give conservatively good performance in all tests.

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    9.2. Accuracy of transformed interpolated images
Interpolated images pose unique challenges for DFT render-
ing. As we discussed in §6.2.4, details such as the choice of the
Fourier-space interpolant and how much padding to use around
the original image signiﬁcantly affect the accuracy of the ren-
dering. We thus need to validate that these choices can be varied
to produce sufﬁciently accurate results.
For this test, we randomly selected a sample 6000 Sérsic
models from the catalogue COSMOS galaxy ﬁts described in
Mandelbaum et al. (2014). For each galaxy in the sample, we
constructed aSersicobject using the best-ﬁtting parameters
in the catalogue, which was then convolved by a COSMOS-
like PSF (a circularAiryproﬁle). This proﬁle was drawn onto
an image with 0.03 arcsec resolution (matching the COSMOS
images). That image was then used to construct anInterpo-
latedImageproﬁle.
For each object in the sample we therefore had the same pro-
ﬁle modelled both as an analytic convolution and as an interpo-
lated image. Small shears were then applied to both models and
the resulting proﬁles were drawn onto images using the DFT
rendering algorithm, although without including the integration
by a pixel. Each proﬁle was convolved by a tiny Gaussian to
force GAL SIM to use the DFT rendering method (as direct ren-
dering would otherwise be used when omitting the pixel convo-
lution).
−0.6 −0.4 −0.2 0.0 0.2 0.4 0.6
g1  (DFT)
−0.00010
−0.00005
0.00000
0.00005
0.00010
∆g1  (DFT - photon)
n = 1.5
n = 6.2
−0.6 −0.4 −0.2 0.0 0.2 0.4 0.6
g2  (DFT)
−0.00010
−0.00005
0.00000
0.00005
0.00010
∆g2  (DFT - photon)
n = 1.5
n = 6.2

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    0.1 0.2 0.3 0.4 0.5 0.6 0.7
σ (DFT) [arcsec]
−0.00001
0.00000
0.00001
0.00002
0.00003
0.00004
0.00005
∆σ (DFT - Photon) [arcsec]
n = 1.5
n = 6.2
Figure 3: Difference between measured shears (upper panel:g1; central panel:
g2; lower panel:σ) for Sérsic proﬁles simulated using the photon-shooting and
DFT rendering methods, plotted against the (shot noise free) shear and size
measured from the DFT image. Results are shown for 30 galaxies with realistic
size and shape distribution, and Sérsic index valuesn = 1.5,6.2. (Note that
the ‘peakiness’ of the high-n proﬁles results in their lowσestimates. The two
samples share the same distributions of half light radii.) The best-ﬁtting lines
are shown, and estimates of the slopesm x,DFT for these and other values ofn
are plotted in Fig. 4.
25
1 2 3 4 5 6 7
Sersic index n
−0.0003
−0.0002
−0.0001
0.0000
0.0001
0.0002
0.0003
Multiplicative slope mDFT
g1
g2
σ
Figure 4: Estimates ofm 1,DFT ,m 2,DFT and m σ,DFT , corresponding to rendering-
induced discrepancies in ellipticityg1,g2 and sizeσ, respectively, as a func-
tion of Sérsic indexn. These slope parameters are deﬁned by equations (74) &
(75) for the differences between measurements from DFT and photon-shooting-
rendered images of Sérsic proﬁles. The shaded region shows the target for
G AL SIM based on not exceeding one tenth of weak lensing accuracy require-
ments for Stage IV surveys such asEuclid(see §9).
10-3 10-2 10-1
folding_threshold
−0.00030
−0.00025
−0.00020
−0.00015
−0.00010
−0.00005
0.00000
Multiplicative slope mDFT
g1
g2
σ
Figure 5: Estimates ofm 1,DFT ,m 2,DFT and m σ,DFT , corresponding to rendering-
induced discrepancies in ellipticityg1,g2 and sizeσ, respectively, as a func-
tion of theGSParamsparameterfolding_threshold. Each point shows
the average from the randomly-selected sample of 270 unmodiﬁed COS-
MOS galaxy models described in §9.1. The rendering parameter fold-
ing_thresholdis described in §6.4 and takes a default value of 5× 10−3,
indicated by the dotted line. As for Fig. 4 these parameters are deﬁned by the

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    model of equations (74) & (75). The shaded region shows the target for GAL -
SIM based on not exceeding one tenth of weak lensing accuracy requirements
for Stage IV surveys (see §9).
Adaptive moments estimates of the change in ellipticity were
seen to be consistent between the parametric model and inter-
polated image at better than 1/10thEuclidrequirements, for all
real and Fourier space interpolants of higher order than bilinear.
Crucially, both were consistent with the known applied shear.
Results for changes in object size were similar. These testsvali-
dated theInterpolatedImagehandling of transformations
for simple input images derived from parametric proﬁles (such
as a Sérsic galaxy convolved with a COSMOS PSF).
The test was then extended to the more complicated case of
RealGalaxyproﬁles. Once again, adaptive moments esti-
mates of the object ellipticity were made before and after ap-
plying a shear. This was compared to the expected shear, cal-
culable given an adaptive moments estimate of the intrinsicel-
lipticity prior to shearing, and the known applied shear. The
RealGalaxyproﬁle was again convolved with a tiny Gaus-
sian PSF prior to rendering (see above), but in this case addi-
tional whitening noise was applied to verify that the presence of
sheared, correlated noise in the output was being appropriately
handled.
This test was repeated for the same sample of 6000 COS-
MOS galaxy images. Fig. 6 shows estimates ofm i,interpfor a
range of Fourier space interpolants, and for two values of the
pad_factorparameter, which speciﬁes how large a region
around the original image to pad with zeroes. A larger value
forpad_factorproduces more accurate results, as shown in
Fig. 6, but is accompanied by large increases in computation
time.
We performed many similar tests to this for a range of trans-
formations (in various combinations) and input parameters. In
all tests performed, settingpad_factor= 4 and using the
two-dimensional quintic interpolant gave results that satisﬁed

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    m i,interp< 2 × 10−4,ci,interp< 2 × 10−5. These results justify
the choice of these as the defaults in GAL SIM . Values ofci,interp
were found to be extremely small in general.
In addition to verifying direct shear response, we also
checked for leakage between shear components, i.e., that ap-
plying shear in one component does not result in an incorrect
level of shear in the other component. The leakage was found
to be consistent with zero and comfortably within requirements
forpad_factorvalues of 4 and 6, for all interpolants tested.
The onlyRealGalaxytest that did not pass our require-
ment was when we simultaneously simulated shears in both
components and a magniﬁcation. In this case we found
mσ,interp∼ (4± 0.4)× 10−4, largely irrespective of the choice
of interpolant. The source of this bias, which is larger thanthe
target 2× 10−4, has not yet been identiﬁed. However, as mag-
niﬁcation is a cosmological probe that is typically noisierthan
shear, this degree of discrepancy is likely to be tolerable for
simulations of magniﬁcation in Stage IV survey data.
9.3. Accuracy of reconvolution
As a ﬁnal demonstration of GAL SIM ’s high precision opera-
tion, we tested that we can accurately apply the reconvolution
algorithm of §6.5 (Mandelbaum et al., 2012). The aim is to rep-
resent the appearance of a test object following an applied shear
gapplied, when viewed at lower resolution.
26

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    3.5 4.0 4.5 5.0 5.5 6.0 6.5 7.0 7.5 8.0
Input pad_factor
−0.0003
−0.0002
−0.0001
0.0000
0.0001
0.0002
0.0003
Multiplicative slope m 1,interp
k interpolants: slope of ∆g1  as a function of
applied g1  [only g1  applied]
cubic
quintic
lanczos3
lanczos4
lanczos5
lanczos7

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    3.5 4.0 4.5 5.0 5.5 6.0 6.5 7.0 7.5 8.0
Input pad_factor
−0.0003
−0.0002
−0.0001
0.0000
0.0001
0.0002
0.0003
Multiplicative slope m 2,interp
k interpolants: slope of ∆g2  as a function of
applied g2  [only g2  applied]
cubic
quintic
lanczos3
lanczos4
lanczos5
lanczos7
Figure 6: Multiplicative biasm i,interpin the relationship between an applied
shear and an adaptive moments estimate of the observed shearforReal-
Galaxyobjects, for various Fourier space interpolants, e.g. cubic, quintic etc.,
and the padding factor (default = 4, indicated by the dotted line). These re-
sults include the handling of correlated noise via the noisewhitening procedure
described in §7.5. The shaded region shows the target for GAL SIM based on
not exceeding one tenth of weak lensing accuracy requirements for Stage IV
surveys (see §9).
This test was carried out usingSersicproﬁles convolved
by a known COSMOS-like PSF (a circularAiryproﬁle), ren-
dered at high resolution (0.03 arcsec/pixel). These images,
along with images of the PSF, were then used as inputs to ini-
tializeRealGalaxyobjects, mimicking the use of real COS-
MOS galaxy images. In the usual manner these objects were
sheared and reconvolved by a broader (ground-based or Stage
IV space-based survey) PSF, then rendered at lower resolution.
Because of the use of an underlying parametric Sérsic proﬁle,
the rendering of which has been validated in §9.1, we can also
render the convolved, sheared objectdirectlyat lower resolution
to provide a reference for comparison. We quantify any error
in the effectively applied shear due to the reconvolution process
asm i,reconvand ci,reconv, deﬁned according to equation (74).
The test was done for 200 proﬁles whose parameters were
selected from the real COSMOS galaxy catalogue described in
Mandelbaum et al. (2014), using random galaxy rotations in an
8-fold ring test conﬁguration (Nakajima & Bernstein, 2007).
Since galaxies with different light proﬁles might be more or
less difﬁcult to accurately render using reconvolution, wemust

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    consider not only the mean values ofm and c, but also investi-
gate their ranges, which could identify galaxy types for which
the method fails to work sufﬁciently accurately even if it issuc-
cessful for most galaxies.
Fig. 7 shows m i,reconv as a function of the fold-
ing_thresholdparameter described in §6.4. Near the
G AL SIM default value of 5×10−3, our requirementm i,reconv <
2 × 10−4 is met comfortably in the ensemble average.
Across the sample of 200 COSMOS galaxies a small frac-
tion (3/200) exceeded our requirement for the defaultfold-
ing_thresholdvalue form 2,reconv. However, we do not be-
lieve that this represents enough of a concern to change the de-
faultGSParamssettings. Provided that a representative train-
ing set of galaxy models (such as the COSMOS sample), of
sufﬁcient size, is used, the variation inm i,reconv seen in Fig. 7
should not prevent simulations using the reconvolution algo-
rithm from being accurate to Stage IV requirements for weak
lensing.
If greater accuracy is required, users wishing to reduce the
impact of these effects can modify the values of theGSParams
according to their needs. In this case, reducingfold-
ing_thresholdby a factor of 10 bringsm 2,reconv within re-
quirements for all 200 galaxies tested. Additive biasesci,reconv
were found to be extremely small (and consistent with zero) in
all cases.
These results shows that the approximations inherent in the
reconvolution process do not signiﬁcantly interfere with GAL -
SIM ’s ability to render accurate images suitable for weak lens-
ing simulations, for a realistic range of galaxy proﬁles drawn
from COSMOS.
9.4. Limitations
While results presented in this Section are encouraging, with
the default settings providing accuracy that comfortably ex-
ceeds our requirements by a factor of 5–10 in many cases, it
must be remembered that no set of tests presented in this arti-
27
cle could be sufﬁcient to positively validate GAL SIM ’s perfor-
mance for all possible future applications. Users of GAL SIM

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    are strongly advised to conduct their own tests, tailored totheir
speciﬁc requirements.
One speciﬁc caveat worthy of mention is the adoption of a
circular PSF for all tests presented. A circularAirywas cho-
sen as a simple approximation to the PSF found in COSMOS
and otherHST images. GAL SIM makes no distinction between
those objects describing PSFs and those describing galaxies
when rendering convolutions of multiple proﬁles. However,it is
possible that a subtle bug or genuine rendering issue might only
be activated for cases wherebothgalaxy and PSF break circular
symmetry. We stress again that no set of tests performed here
can cover all possible uses of the code. Where data properties
such as the PSF are known we encourage GAL SIM users to per-
form their own validation and adjust the rendering parameters
as required for their particular use case.
Another caveat is that we only used a particular set of COS-
MOS galaxies for the training sample. It is plausible that galaxy
models drawn from a population with a different redshift dis-
tribution to the COSMOS sample, or imaged in a ﬁlter other
than F814W, might have sufﬁciently different morphological
characteristics to fail the rendering requirements adopted in this
work. In future it will be of value to understand the marginal,
m σ,interp≃ 4 ×10−4 failure of galaxy size transformations in the
RealGalaxytests when both shear and magniﬁcation were
applied (see §9.2).
In many cases, therefore, users may ﬁnd it necessary to mod-
ify and reﬁne the tests presented here, especially where thein-
puts and requirements of their analyses differ signiﬁcantly from
the assumptions adopted. Some of the tests in this Section will
hopefully serve as a useful starting point for these investiga-
tions.
10. Performance
While the paramount consideration in GAL SIM is the accu-
racy of the renderings, especially with respect to the shapes,
we have also paid considerable attention to making the code as
fast as possible. Code optimization is of course a wide ranging

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    topic, and we will not attempt to go into detail about all the op-
timizations included in the GAL SIM code. We just mention a
few optimizations that were particularly helpful and give some
estimates of the timings for typical use cases.
10.1. Optimizations
The most important performance decision was to use C++
for all time-critical operations. The Python layer provides a
nice front-end user interface, but it is notoriously difﬁcult to
do serious coding optimization in Python. So for all signif-
icant calculations, GAL SIM calls C++ functions from within
Python, where we have used the normal kinds of optimization
techniques that are standard with C and C++ code: precomput-
ing values that will be used multiple times, having tight inner
loops, using iterators to be more amenable to vectorizationby
the compiler, using lookup tables and LRU caches, etc.
10-3 10-2 10-1
folding_threshold
−0.0004
−0.0002
0.0000
0.0002
0.0004
Multiplicative slope m reconv
g1
g2
Figure 7: Multiplicative slopem i,reconvfor the reconvolution test of §9.3, forg1
and g2, as a function of thefolding_thresholdparameter (cf. §6.4). The
exterior error bars show the full range of values for the 200 models tested, and
the points and interior error bars show the mean and standarderror. The shaded
region shows the target for GAL SIM based on not exceeding one tenth of weak
lensing accuracy requirements for Stage IV surveys (see §9). The default value
offolding_thresholdis indicated by the dotted line.
The FFTs for computing convolutions in DFT rendering nor-
mally constitute the bulk of the calculation time. For these, we
use the excellentFFTW package (Frigo & Johnson, 2005). The
calculations are fastest when the image size is either an exact
power of 2, or 3 times a power of 2, so GAL SIM pads the im-
ages to meet this criterion before performing the FFT. Aside
from this consideration, we only use as large an FFT image as
is required to achieve the desired accuracy. This balance isone
of the principal speed/accuracy tradeoffs discussed in §6.4.

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    For some DFT calculations, we can avoid the two-
dimensional FFT entirely by turning it into a one-dimensional
Hankel transform. This is possible when the proﬁle being trans-
formed is radially symmetric, as are many of the analytic pro-
ﬁles. Iff(r,θ) = f(r), then the Fourier transform is similarly
radially symmetric:
˜
f(k)=
∫∞
0
rdr
∫2π
0
f(r,θ)eikrcos(θ) dθ (78)
= 2π
∫∞
0
f(r)J0(kr)rdr (79)
This optimization is particularly effective for Sérsic proﬁles.
The large dynamic range of these proﬁles, especially forn >3,
means that a two-dimensional FFT would require a very large
image to achieve the appropriate accuracy. It is signiﬁcantly
faster to precompute the one-dimensional Hankel transform
˜
f(k), and use that to ﬁll in thek-space values.
The integration package in GAL SIM uses an efﬁcient, adap-
tive Gauss-Kronrod-Patterson algorithm (Patterson, 1968). It
starts with the 10-point Gaussian quadrature abscissae andcon-
tinues adding points at optimally spaced additional locations
28
until it either converges or reaches 175 points. If the integral
has not converged at that point, it splits the original region in
half and tries again on each sub-region, continuing in this man-
ner until all regions have converged. This algorithm is usedin
G AL SIM for Hankel transforms, real-space integration, cumu-
lative probability integrals for photon shooting, calculating the
half-light-radius of Sérsic proﬁles, and a few other placeswhere
integrations are required.
Matrix calculations do not generally account for a large share
of the running time, but to make these as efﬁcient as possible,
we use the TMV library30, which calls the system BLAS library
when appropriate if such a system library is available (revert-
ing to native code otherwise). The matrix calculations are thus
about as efﬁcient as can be expected on a given platform.
One calculation required us to devise our own efﬁcient func-
tion evaluation. For interpolated images using the Lanczosin-
terpolant, Fourier-space calculations require evaluation of the

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    Sine integral:
Si(x)=
∫x
0
sint
t dt (80)
The standard formulae from Abramowitz & Stegun (1964) §5.2
for computing this efﬁciently were only accurate to about 10−6.
This was not accurate enough for our needs, and we could
not ﬁnd any other source for a more accurate calculation. We
therefore developed our own formulae for efﬁciently evalu-
ating Si(x), accurate to 10−16. The formulae are given in
Appendix B.
10.2. Parallelization
Another important optimization happens in the Python layer.
When running GAL SIM using a conﬁguration ﬁle, rather than
writing Python code, it is very easy to get the code to run using
multiple processes using the conﬁguration parameternproc.
Of course, experienced Python programmers can also do this
manually, but multiprocessing in Python is not extremely user
friendly, so it can be convenient to take advantage of this paral-
lelism already being implemented in GAL SIM ’s conﬁguration
ﬁle parser.
10.3. Timings
The time it takes for GAL SIM to render an image depends
on many details of the proﬁles and the image on which they are
being rendered. Some proﬁles tend to take longer than others,
and the size of the object relative to the pixel scale of the ﬁnal
image also matters.
For most analytic proﬁles, if the image scale is not much
smaller than the Nyquist scale of the object, rendering using
the DFT method will generally take of order 0.01 seconds or
less per object. For very many purposes, this kind of proﬁle is
perfectly appropriate, and it can include a reasonable amount of
complication including multiple components to the galaxy such
a bulge plus disk model, offsets of those components, multi-
component PSFs, etc.
30https://code.google.com/p/tmv-cpp/
Models that include interpolated images take longer. This
includes models with anOpticalPSFcomponent or aRe-
alGalaxy. Such proﬁles typically take of order 0.1 seconds
per object for typical sizes of the interpolated images, butthe
time is highly dependent on the size of the image being used to

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    deﬁne the proﬁle.
The running time for photon shooting of course scales lin-
early with the number of photons. The crossover point where
photon shooting is faster than DFT rendering depends on the
proﬁle being rendered, but it is typically in the range of 103–
104 photons. So for faint objects, it can be signiﬁcantly faster
to use the photon-shooting method.
10.4. Potential speed pitfalls
There are a number of potential pitfalls that can lead to
slower than normal rendering, which are worth highlighting:
• Whitening.Proﬁles that use aRealGalaxycan be par-
ticularly slow if the resulting image is whitened (cf. §7.5)
to remove the correlated noise that is present in the origi-
nalHST images (and gets exacerbated by the PSF convolu-
tion). The whitening step can increase the time per object
to about 1 second, although it varies depending on details
such as the ﬁnal pixel scale, what kind of PSF is used, etc.
• Pixel size. Using a DFT to render images with very
small pixels relative to the size of the galaxy can be very
slow. The time required to perform the FFTs scales as
O(N 2 logN ) whereN is the number of pixels across for
the image, so a moderate increase in the size of the galaxy
relative to the pixel scale can make a big difference in the
running time.
• Sérsic proﬁles with varying index.Sérsic galaxies require
pre-computation of some integrals for each Sérsic index
used. When simulating manyn = 3.3 galaxies, the setup
time will be amortized over many galaxies and is thus ir-
relevant. When using a different indexn for each galaxy
though, the setup must be done for each galaxy, potentially
dominating the running time. Thus, it is better to selectn
from a list of a ﬁnite number of values rather than letting
it varying continuously within some range.
• Variable optical PSF parameters.The OpticalPSF
class similarly has a large setup cost to compute the
Fourier transform of the wavefront in the pupil plane. If
there is a single PSF for the image, this setup cost is
amortized over all the objects, but for a spatially variable

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    PSF (which is more realistic), each object will require a
new setup calculation. The variable PSF branches of the
GREAT3 challenge (Mandelbaum et al., 2014) were the
most time-consuming to generate for this reason.
• Complicated wavelength dependence.Drawing chromatic
objects with complex SEDs through non-trivial band-
passes can take quite a long time. The surface brightness
proﬁle needs to be integrated over the relevant range of
29
wavelengths. The more complicated the SED and band-
pass are, the more samples are required to perform the in-
tegration. Thus, depending on the purpose of the images
being rendered, it may be advisable to use simple SEDs
and/or bandpasses, instead of more realistic ones. Opti-
mizations to this process for non-trivial chromatic objects
are being incorporated into future versions of GAL SIM .
10.5. Example output
Figure 8 shows a portion of an image that can be produced
by GAL SIM . This particular image is from a simulation that is
intended to approximate an LSST focal plane.
The simulation has an object density of 70 objects per square
arcminute. The galaxies are bulge plus disk models, and the
PSF includes both atmospheric seeing and an optical compo-
nent with the appropriate obscuration for the LSST telescope,
struts, and plausible aberrations. 20% of the objects are stars.
The ﬂuxes of both the galaxies and the stars follow a power law
distribution, as does the size distribution of the galaxies, and
there is an applied cosmological lensing ﬁeld including both
shear and magniﬁcation. The noise model includes both Gaus-
sian read noise and Poisson noise on the counts of the detected
electrons.
The conﬁguration ﬁle to build this image31 is remarkably
short (just 122 lines), especially considering how many real-
istic data features are included. This example showcases why
we consider the conﬁguration mode to be one of the strengths
of GAL SIM . Even for users who are already comfortable writ-
ing Python code, the conﬁguration ﬁles can be easier to set up

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    and get running in many cases.
Each 4K×4K chip in this simulation takes about 3 minutes to
render on a modern laptop using a single core. The simulation
is set to use as many processors as are available, and with 8
cores running at once, the whole ﬁeld of view (189 chips in all)
can be rendered in a bit more than an hour.
Currently GAL SIM is unable to simulate many of the features
of real images including saturation, bleeding, vignetting, cos-
mic rays, and the like (cf. §11), so those features are not shown
here. For this image, we also chose to cut off the size distribu-
tion at 20 arcsec to avoid the rare objects that would requirean
extremely large FFT.
Despite these apparent shortcomings, this kind of image is
still very useful for studying image processing algorithms. In-
deed, it is often helpful to intentionally make these and other
simpliﬁcations to study the behavior of a particular algorithm.
Images similar to the one shown in Figure 8 have been used
to study the effects of blending, star-galaxy separation algo-
rithms, and shear estimation. For these and many other inves-
tigations, complete realism of the simulated images is not re-
quired.
11. Effects not in GAL SIM
It is worth mentioning some of the many physical effects in
optical and near-infrared astronomical observations thatG AL -
31 Available publicly athttp://ls.st/xj0.
SIM cannot yet model. Many of these effects will be important
to model and explore to help ensure that accurate measurements
will be possible from future extragalactic survey data:
• Physical atmospheric PSF models.Examples of public
software that can be used to generate physically motivated,
multi-layer phase screen models of atmospheric PSFs in-
clude ARROYO 32, and the LSST IM SIM 33 software (Pe-
terson et al. in prep.). While the possibility of adding
such an atmospheric PSF module to GAL SIM was investi-
gated as part of preparatory work for the GREAT3 project
(Mandelbaum et al., 2014), this functionality is still lack-
ing.

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    • Non-linear detector effects. G AL SIM cannot yet model
pixel saturation or bleeding (e.g. Bertin, 2009), interpixel
capacitance (e.g. Moore et al., 2004) and other forms of
cross-talk, all of which affect image ﬂux and shape deter-
mination.
• Image artifacts such as ghosts, detector persistence.
These effects (e.g. Wynne et al., 1984; Meng et al., 2013;
Long et al., 2010; Barrick, Ward, & Cuillandre, 2012;
Anderson et al., 2014) can be difﬁcult to model, or even
classify and remove, when measuring the properties of
astronomical objects in an object-by-object fashion (the
current standard procedure34). Simulating observations
with these effects will therefore be important to be able
to demonstrate reliable measurements in their presence.
• Cosmic rays. Simulations of these effects (such as, e.g.,
Rolland et al., 2008) are likely to be an important consid-
eration for imaging in upcoming Stage IV surveys, par-
ticularly for space missions at the second Lagrange point
(e.g. Barth, Isaacs, & Poivey, 2000).
• Near ﬁeld contaminants such as satellite trails and mete-
ors.These effects, of relevance to ground-based imaging,
are not currently supported by GAL SIM . Like cosmic rays
and instrumental artifacts such as ghosts and persistence,
these effects will place stringent demands on object clas-
siﬁcation procedures for upcoming survey experiments.
• Flexion. Although trivially described using a photon-
shooting approach, simulations of non-afﬁne image trans-
formations such as weak gravitational ﬂexion are incom-
patible with the Fourier space rendering of individual pro-
ﬁles described in §6. Flexion is not currently implemented
in GAL SIM . However, the GAL FLEX 35 package is a stan-
dalone, open-source Python module that can be integrated
with GAL SIM via a NUM PY array interface.
• Vignetting, variable quantum efﬁciency, and ﬂat ﬁelding
effects.No variation in the efﬁciency of photon detection
32http://cfao.ucolick.org/software/arroyo.php
33http://lsst.astro.washington.edu/

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    34Although seehttp://thetractor.org/
35http://physics.drexel.edu/~jbird/galflex/
30
Figure 8: A portion of a GAL SIM simulation of an LSST focal plane. This section is about 5 arcminutes across with a number density of 70 objects per square
arcmin, of which 80% are galaxies and 20% are stars.
as a function of position in the output image is currently
included in GAL SIM , including variation within pixels. It
will be possible to address large scale effects in a relatively
straightforward post-processing step. However, signiﬁcant
intra-pixel quantum efﬁciency variation may require care-
ful design to render efﬁciently.
• Complicated WCS functions.Recent studies of the DE-
Cam and LSST detectors (Plazas et al., 2014; Rasmussen,
2014) have revealed complicated astrometric shifts, in-
cluding edge distortions and tree-rings. These are not cur-
rently modeled by any existing WCS package, so it would
require a custom implementation to include these effects
in GAL SIM .
Many further possibilities for expanding and improving
G AL SIM capabilities can be found in already existing func-
tionality. TheOpticalPSFclass described in §3.2.2 could
be extended to a more general treatment of optical wavefronts
by allowing an arbitrary number of Zernike coefﬁcients to be
speciﬁed on input. Support for photon shooting ofShapelet
objects (see §3.3.2), although a considerable task, would also
be a valuable addition to GAL SIM . It is hoped that, through the
open and collaborative development pattern already established
within the GAL SIM project, many of these capabilities will be
added to GAL SIM in the future.
12. Conclusions
We have described GAL SIM : the modular galaxy image sim-
ulation toolkit. A primary motivation for the project was the de-
sire for an open, transparent, and community-maintained stan-
dard toolkit for high precision simulations of the deep extra-
galactic imaging expected in upcoming Stage III and Stage IV
surveys. We have described the range of physical models cho-

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    sen as the basis for describing astronomical objects in GAL -
SIM , and the support for their description in a range of world
coordinate systems. We have also described the mathematical
principles used in the multiple strategies supported by GAL SIM
for rendering these models onto images, and for adding noise.
A number of the techniques employed by GAL SIM are novel,
including the photon shooting of a range of proﬁles includ-
ingInterpolatedImageobjects (see §6.3.3) and noise
whitening (§7.5). The consistent handling of astronomicalob-
ject transformation and rendering under a variety of WCS trans-
formations, described in §5, is also new in the ﬁeld of astronom-
ical image simulation. GAL SIM is unique in bringing all these
features together under a simple, highly ﬂexible, class library
interface.
An important part of any software project is testing and val-
idation. The provision of multiple parallel methods for ren-
dering images (see §6), a capability unique to GAL SIM among
comparable simulation packages, played a vitally important
role in this process.
In §9 we showed results from a number of tests demonstrat-
ing that GAL SIM output can describe weak lensing transforma-
tions such as shear and magniﬁcation at the level of accuracyre-
quired for Stage IV surveys such asEuclid,LSST and WFIRST-
AFTA . This was demonstrated for highly challenging analytic
proﬁles (theSersicclass, see §9.1), for surface brightness
proﬁles derived from images such as theInterpolatedIm-
ageand RealGalaxyclasses (see §9.2), and for the recon-
volution algorithm (see §9.3).
The accuracy of rendering results can be tuned using input
parameters, and using theGSParamsstructure described in
§6.4. Less stringent requirements will yield faster execution,
but at the cost of lowering rendering accuracy in output im-
ages. As no set of validation tests can completely cover all us-
31
age scenarios, the tests of §9 should be modiﬁed by users of the
G AL SIM software to tailor them to each application’s speciﬁc

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    requirements.
As discussed in §11, there are a number of important effects
that GAL SIM cannot yet simulate, but that may signiﬁcantly
impact data analysis for upcoming surveys. Work is expected
to continue in these interesting areas: while the development
and support of GAL SIM began in early 2012, it is an ongoing
project that continues to build on increasing numbers of users
(and developers).
As well as being used to generate the images for the GREAT3
challenge (Mandelbaum et al., 2014), GAL SIM now provides
a considerable open-source toolkit for the simulation of extra-
galactic survey images. Having been shown to meet demanding
tolerances on rendering accuracy in a number of tests, GAL SIM
simulations can be used as a benchmark for development or
common reference point for code comparison. It also provides
an accessible, well-documented reference codebase. GAL SIM
is easily extended, or can be used simply as a class library in
the development of further astronomical image analysis appli-
cations. In these respects GAL SIM achieves its primary aims,
and will become an increasingly powerful toolkit for astronom-
ical image simulation following development that is planned for
the near future.
Acknowledgments
We wish to thank the two anonymous referees whose insight-
ful comments signiﬁcantly improved the paper. This project
was supported in part by NASA via the Strategic University
Research Partnership (SURP) Program of the Jet Propulsion
Laboratory, California Institute of Technology. Part of BR’s
work was done at the Jet Propulsion Laboratory, California In-
stitute of Technology, under contract with NASA. BR, JZ and
TK acknowledge support from a European Research Council
Starting Grant with number 240672. MJ acknowledges support
from NSF award AST-1138729. RM was supported in part by
program HST-AR-12857.01-A, provided by NASA through a
grant from the Space Telescope Science Institute, which is oper-
ated by the Association of Universities for Research in Astron-

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    omy, Incorporated, under NASA contract NAS5-26555; and in
part by a Sloan Fellowship. HM acknowledges support from
Japan Society for the Promotion of Science (JSPS) Postdoc-
toral Fellowships for Research Abroad and JSPS Research Fel-
lowships for Young Scientists. PM is supported by the U.S. De-
partment of Energy under Contract No. DE- FG02-91ER40690.
The authors acknowledge the use of the UCL Legion High Per-
formance Computing Facility (Legion@UCL), and associated
support services, in the completion of this work. This work
was supported in part by the National Science Foundation un-
der Grant No. PHYS-1066293 and the hospitality of the Aspen
Center for Physics.
32
Appendix A. Conventions in the lensing engine
Appendix A.1. Grid parameters
All calculations in the GAL SIM lensing engine (see §4) approximate real continuous functions using a discrete, ﬁnite grid. The
real-space grid is deﬁned by
L = length of grid along one dimension (angular units) (A.1)
d = spacing between grid points (angular units) (A.2)
N = number of grid points along one dimension= L/d. (A.3)
There is a comparable grid in Fourier-space (i.e., sameN ). Given the parameters of the real-space grid, thekmin along one dimension
is 2π/L, so we can think of this quantity as the grid spacing in Fourier space, i.e.,kmin = ∆k. This value ofkmin corresponds to a
Fourier mode that exactly ﬁts inside of our square grid (in one dimension). Thek range, again in one dimension, is fromk1 = −π/d
toπ/d, i.e.,|k1| < kmax = π/d. This corresponds to a mode that is sampled exactly twice (the minimum possible) given our choice
of grid spacing. For the two-dimensional grid, the maximum value of|k| is then
√
2π/d.
Appendix A.2. Fourier transform properties
The convention for the Fourier transform deﬁned by equations (34) & (35) is adopted throughout, as this is the form typically
used for describing the statistics of cosmological shear and matter ﬁelds. Unlike the convention typically used in computing and
signals processing, and in the standard deﬁnition of the Discrete Fourier Transform (DFT), this convention is non-unitary and uses

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    an angular (rather than normal) frequency in the exponent36. This introduces some additional factors of 2πinto standard results,
and so here we re-express these results using the non-unitary, angular frequency convention.
It can be readily shown that if we deﬁneg(xL)≡ f(x), the following well-known identity holds:
F{g(xL)} = 1
L˜g
( k
L
)
. (A.4)
If we further deﬁnes(h + x)≡ g(x) then it is straightforward to show that
F{s(h + x)} = eikh˜s(k). (A.5)
There is an additional factor of 2πin the exponent when this property of Fourier transforms is expressed using the normal (rather
than angular) frequency convention.
The most important result for approximating continuous functions using DFTs is the Poisson summation formula, which under
the conventions of equations (34) & (35) may be stated as
∞∑
n=−∞
f(n)=
∞∑
q=−∞
˜f(2πq) (A.6)
for integersn and q. It should be noted that in the normal frequency, unitary transform convention form of the Poisson summation
formula the 2πwithin˜
f(2πq) is absent. Using equations (A.4) & (A.5) we arrive at the following useful expression of the Poisson
summation formula:
∞∑
n=−∞
f(nL + x)= 1L
∞∑
q=−∞
˜
f
( 2πqL
)
ei2πxq/L . (A.7)
By substituting∆k ≡ kmin = 2π/L we write this as
∞∑
n=−∞
f
( 2πn
∆k + x
)
=
( ∆k
2π
) ∞∑
q=−∞
˜f(q∆k)eix∆kq. (A.8)
36For a discussion of transform conventions seehttp://en.wikipedia.org/wiki/Fourier_transform#Other_conventions
33
Appendix A.3. Fourier transform of discrete samples of the power spectrum
Let us deﬁne the following dimensionless function, which takes samples from a power spectrum:
P∆k[q,p]≡ (∆k)2P(q∆k,p∆k). (A.9)
We will use square brackets to denote functions with discrete, integer input variables, as here. We will also usen,m for integer
indices in real space summations, andq,p in Fourier space. It can then be shown that
F−1







∞∑
q,p=−∞
δ(k1 −q∆k)δ(k2 − p∆k)P∆k[q,p]






=
∞∑
n,m =−∞
ξ+
(
θ1 − 2πn
∆k ,θ2 − 2πm
∆k
)
, (A.10)
where we have used the Fourier series expression for the Dirac comb function, and the convolution theorem. We note that this

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    expression is still continuous, but describes an inﬁnite, periodic summation (of periodL = 2π/∆k) of copies of the correlation
functionξ+. For sufﬁciently small∆k, these copies may be spaced sufﬁciently widely in the real domain to be able to learn much
aboutξ+(θ1,θ2) in the non-overlapping regions. We therefore deﬁne this function as
ξ2π
∆k
(θ1,θ2)≡
∞∑
n=−∞
ξ+
(
θ1 − 2πn
∆k ,θ2 − 2πm
∆k
)
. (A.11)
Using the expression of the Poisson summation formula in equation (A.8), we can also write
ξ2π
∆k
(θ1,θ2)=
∞∑
q,p=−∞
( ∆k
2π
) 2
P(q∆k,p∆k)ei∆k(θ1q+θ2 p) = 1
(2π)2
∞∑
q,p=−∞
P∆k[q,p]ei∆k(θ1q+θ2 p), (A.12)
This is in fact an expression for the inverse of the Discrete Time Fourier Transform (DTFT), although this result is normally derived
using unitary conventions for the transform pair.
The expression in equation (A.12) is periodic with period 2π/∆k = L. All of the information it contains aboutξ+(θ1,θ2) is
therefore also contained in one period of the function only.For approximating this information discretely, as desiredin numerical
analysis, we can imagine takingN equally spaced samples of the function in equation (A.12) along a single periodL in each
dimension. These samples are therefore separated by∆θ= 2π/∆kN = d in real space, and we deﬁne the sampled function itself as
ξ∆θ[n,m ]≡ ξ2π
∆k
(n∆θ,m ∆θ)= 1
(2π)2
∞∑
q,p=−∞
P∆k[q,p]ei2π(qn+pm )/N , (A.13)
for the integer indicesn,m = 0,1,..., N −1, by substitution into equation (A.12). Using the periodicity of the exponential term in
the expression above, this may be written as
ξ∆θ[n,m ]= 1
(2π)2
N −1∑
q,p=0
P N [q,p]ei2π(qn+pm )/N (A.14)
where we have deﬁned
P N [q,p]≡
∞∑
i,j=−∞
P∆k[q −iN,p − jN]. (A.15)
Needless to say, in order to be able to calculate the values ofP N [q,p] in practice we must also truncate theP∆k sequence to be ﬁnite
in length. Averycommon choice is to use the same numberN of samples in both real and Fourier space. Choosing to use only N
samples fromP∆k then gives
ξ∆θ[n,m ]= 1
(2π)2
N −1∑
q,p=0
P∆k[q,p]ei2π(qn+pm )/N

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    = 1
N 2 (∆θ)2
N −1∑
q,p=0
P(q∆k,p∆k)ei2π(qn+pm )/N . (A.16)
For greater detail regarding this calculation, please see the lensing engine document in the GAL SIM repository.37
37https://github.com/GalSim-developers/GalSim/blob/master/devel/modules/lensing_engine.pdf
34
The relationship in equation (A.16) is in fact the inverse Discrete Fourier Transform for our non-unitary convention. The more
usual deﬁnition of the inverse DFT, and that adopted by many DFT implementations (including the NUM PY package in Python), is
f[n,m ]= numpy.fft.ifft2
( ˜
f[p,q]
)
≡ 1N 2
N −1∑
q,p=0
˜
f[q,p]ei2π(qn+pm )/N (N UM PY convention). (A.17)
(The factor of 1/N 2 here is often found in conventions for the inverse DFT, and ensures that the DFT followed by the inverse DFT
yields the original, input array.) The Fast Fourier Transform algorithm allows the DFT to be calculated very efﬁciently.
Appendix A.4. Generating Gaussian ﬁelds
Using equation (A.16) we see how to construct a realization of a Gaussian random lensing ﬁeld on a grid, with an ensemble
average power spectrum that is approximatelyP(k). We create the following complex, 2D array of dimensionN in Fourier space:
˜κ[p,q]=˜κE [p,q]+i˜κB [p,q], (A.18)
where˜κE is deﬁned in terms of the desired E-mode power spectrumP E as
˜κE [p,q]= 1N ∆θ
√
P E (p∆k,q∆k)
2 {N(0,1)+iN(0,1)}, (A.19)
and likewise for˜κB . HereN(0,1) denotes a standard Gaussian random deviate drawn independently at each [p,q] array location.
This complex-valued Fourier-space convergence can be usedto construct the Fourier-space shear ﬁeld via38
˜g = e2iψ˜κ, (A.20)
where e2iψ is the phase of thek vector deﬁned ask = ∆k(p +iq). It can be seen that⟨˜g[p,q]˜g∗[p′,q′]⟩= δp′
p δq′
q P(|k|)/(N ∆θ)2 where
|k| = ∆k
√
p2 +q2. Taking the inverse DFT of˜g provides the realization of the Gaussian lensing ﬁeldg[n,m ] on a grid in real space,
where the real (imaginary) parts ofg[n,m ] correspond to the ﬁrst (second) shear components. From equation (A.16),g[n,m ] will
be correctly scaled to have discrete correlation functionξ∆θ[n,m ] by construction.

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    Appendix B. Efﬁcient evaluation of the Sine and Cosine integrals
The trigonometric integrals are deﬁned as
Si(x)=
∫x
0
sint
t dt= π
2 −
∫∞
x
sint
t dt (B.1)
Ci(x)= γ+lnx +
∫x
0
cost−1
t dt= −
∫∞
x
cost
t dt (B.2)
where γis the Euler-Mascheroni constant. In GAL SIM , calculations involving Lanczos interpolants require an efﬁcient calculation
of Si(x). As we were unable to ﬁnd a source for an efﬁcient calculation that was suitably accurate, we developed our own, which
we present here. We do not use Ci(x) anywhere in the code, but for completeness, we provide a similarly efﬁcient and accurate
calculation of it as well.
For small arguments, we use Padé approximants of the convergent Taylor series
Si(x)=
∞∑
n=0
(−1)nx2n+1
(2n +1)(2n +1)! (B.3)
Ci(x)= γ+lnx +
∞∑
n=1
(−1)nx2n
2n(2n)! (B.4)
38See, for example, Kaiser & Squires (1993), but note that there is a sign error in equation 2.1.12 in that paper that is corrected in equation 2.1.15.
35
Using the Maple software package39, we derived the following formulae, which are accurate to better than 10−16 for 0≤ x ≤ 4:
Si(x)= x ·





































1 −4.54393409816329991 ·10−2 · x2 +1.15457225751016682 ·10−3 · x4
−1.41018536821330254 ·10−5 · x6 +9.43280809438713025 ·10−8 · x8
−3.53201978997168357 ·10−10 · x10 +7.08240282274875911 ·10−13 · x12
−6.05338212010422477 ·10−16 · x14
1 +1.01162145739225565 ·10−2 · x2 +4.99175116169755106 ·10−5 · x4
+1.55654986308745614 ·10−7 · x6 +3.28067571055789734 ·10−10 · x8
+4.5049097575386581 ·10−13 · x10 +3.21107051193712168 ·10−16 · x12





































(B.5)
Ci(x)= γ+ln(x)+
x2 ·





































−0.25 +7.51851524438898291 ·10−3 · x2 −1.27528342240267686 ·10−4 · x4
+1.05297363846239184 ·10−6 · x6 −4.68889508144848019 ·10−9 · x8
+1.06480802891189243 ·10−11 · x10 −9.93728488857585407 ·10−15 · x12
1 +1.1592605689110735 ·10−2 · x2 +6.72126800814254432 ·10−5 · x4

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    +2.55533277086129636 ·10−7 · x6 +6.97071295760958946 ·10−10 · x8
+1.38536352772778619 ·10−12 · x10 +1.89106054713059759 ·10−15 · x12
+1.39759616731376855 ·10−18 · x14





































(B.6)
For x >4, one can use the helper functions:
f(x)≡
∫∞
0
sin(t)
t+ x dt=
∫∞
0
e−xt
t2 +1 dt= Ci(x) sin(x)+
( π
2 −Si(x)
)
cos(x) (B.7)
g(x)≡
∫∞
0
cos(t)
t+ x dt=
∫∞
0
t e−xt
t2 +1dt= −Ci(x) cos(x)+
( π
2 −Si(x)
)
sin(x) (B.8)
using which, the trigonometric integrals may be expressed as
Si(x)= π
2 − f(x) cos(x)−g(x) sin(x) (B.9)
Ci(x)= f(x) sin(x)−g(x) cos(x) (B.10)
In the limit asx → ∞, f(x) → 1/x and g(x) → 1/x2. Thus, we can use Chebyshev-Padé expansions of1√y f
(
1√y
)
and 1
y g
(
1√y
)
in the interval 0..1
42 to obtain the following approximants, good to better than 10−16 forx ≥ 4:
f(x)= 1
x ·















































1 +7.44437068161936700618 ·102 · x−2 +1.96396372895146869801 ·105 · x−4
+2.37750310125431834034 ·107 · x−6 +1.43073403821274636888 ·109 · x−8
+4.33736238870432522765 ·1010 · x−10 +6.40533830574022022911 ·1011 · x−12
+4.20968180571076940208 ·1012 · x−14 +1.00795182980368574617 ·1013 · x−16
+4.94816688199951963482 ·1012 · x−18 −4.94701168645415959931 ·1011 · x−20
1 +7.46437068161927678031 ·102 · x−2 +1.97865247031583951450 ·105 · x−4
+2.41535670165126845144 ·107 · x−6 +1.47478952192985464958 ·109 · x−8
+4.58595115847765779830 ·1010 · x−10 +7.08501308149515401563 ·1011 · x−12
+5.06084464593475076774 ·1012 · x−14 +1.43468549171581016479 ·1013 · x−16
+1.11535493509914254097 ·1013 · x−18















































(B.11)
g(x)= 1
x2 ·















































1 +8.1359520115168615 ·102 · x−2 +2.35239181626478200 ·105 · x−4
+3.12557570795778731 ·107 · x−6 +2.06297595146763354 ·109 · x−8
+6.83052205423625007 ·1010 · x−10 +1.09049528450362786 ·1012 · x−12

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    +7.57664583257834349 ·1012 · x−14 +1.81004487464664575 ·1013 · x−16
+6.43291613143049485 ·1012 · x−18 −1.36517137670871689 ·1012 · x−20
1 +8.19595201151451564 ·102 · x−2 +2.40036752835578777 ·105 · x−4
+3.26026661647090822 ·107 · x−6 +2.23355543278099360 ·109 · x−8
+7.87465017341829930 ·1010 · x−10 +1.39866710696414565 ·1012 · x−12
+1.17164723371736605 ·1013 · x−14 +4.01839087307656620 ·1013 · x−16
+3.99653257887490811 ·1013 · x−18















































(B.12)
39http://www.maplesoft.com/
36
Thus we can calculate Si(x) to double precision accuracy for any value ofx. In GAL SIM , all of the above polynomials are
implemented using Horner’s rule, so they are very efﬁcient to evaluate.
References
Abazajian, K. N., Adelman-McCarthy, J. K., Agüeros, M. A., et al. 2009, ApJS, 182, 543
Abramowitz, M., & Stegun, I. 1964, Handbook of MathematicalFunctions, 5th edn. (New York: Dover)
Airy, G. B. 1835, Transactions of the Cambridge Philosophical Society, 5, 283
Albrecht, A., Bernstein, G., Cahn, R., et al. 2006, ArXiv Astrophysics e-prints, astro-ph/0609591
Amara, A., & Réfrégier, A. 2008, MNRAS, 391, 228
Anderson, R. E., Regan, M., Valenti, J., & Bergeron, E. 2014,ArXiv e-prints, arXiv:1402.4181
Antilogus, P., Astier, P., Doherty, P., Guyonnet, A., & Regnault, N. 2014, Journal of Instrumentation, 9, C3048
Bacon, D. J., Goldberg, D. M., Rowe, B. T. P., & Taylor, A. N. 2006, MNRAS, 365, 414
Barrick, G. A., Ward, J., & Cuillandre, J.-C. 2012, in Society of Photo-Optical Instrumentation Engineers (SPIE) Conference Series, V ol. 8453, High Energy,
Optical, and Infrared Detectors for Astronomy V , article id. 84531K, 8 pp.
Bartelmann, M. 1996, A&A, 313, 697
—. 2010, Classical and Quantum Gravity, 27, 233001
Barth, J., Isaacs, J., & Poivey, C. 2000, The Radiation Environment for the Next Generation Space Telescope, Tech. rep.
Becker, M. R. 2013, MNRAS, 435, 115
Bernstein, G. M. 2010, MNRAS, 406, 2793
Bernstein, G. M., & Armstrong, R. 2014, MNRAS, 438, 1880

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    Bernstein, G. M., & Gruen, D. 2014, PASP, 126, 287
Bernstein, G. M., & Jarvis, M. 2002, AJ, 123, 583
Bertin, E. 2009, Mem. Societa Astronomica Italiana, 80, 422
Born, M., & Wolf, E. 1999, Principles of Optics
Bridle, S., Shawe-Taylor, J., Amara, A., et al. 2009, Annalsof Applied Statistics, 3, 6
Bridle, S., Balan, S. T., Bethge, M., et al. 2010, MNRAS, 405,2044
Calabretta, M. R., & Greisen, E. W. 2002, A&A, 395, 1077
Casertano, S., de Mello, D., Dickinson, M., et al. 2000, AJ, 120, 2747
Ciotti, L., & Bertin, G. 1999, A&A, 352, 447
Cropper, M., Hoekstra, H., Kitching, T., et al. 2013, MNRAS,431, 3103
Cypriano, E. S., Amara, A., V oigt, L. M., et al. 2010, MNRAS, 405, 494
de Jong, J. T. A., Verdoes Kleijn, G. A., Kuijken, K. H., & Valentijn, E. A. 2013, Experimental Astronomy, 35, 25
de Vaucouleurs, G. 1948, Annales d’Astrophysique, 11, 247
—. 1959, AJ, 64, 397
Duncan, C. A. J., Joachimi, B., Heavens, A. F., Heymans, C., &Hildebrandt, H. 2014, MNRAS, 437, 2471
Fried, D. L. 1966, Journal of the Optical Society of America (1917-1983), 56, 1372
Frigo, M., & Johnson, S. G. 2005, Proceedings of the IEEE, 93,216, special issue on “Program Generation, Optimization, and Platform Adaptation”
Fruchter, A. S., & Hook, R. N. 2002, PASP, 114, 144
Goldberg, D. M., & Bacon, D. J. 2005, ApJ, 619, 741
Heymans, C., Van Waerbeke, L., Bacon, D., et al. 2006, MNRAS,368, 1323
Heymans, C., Van Waerbeke, L., Miller, L., et al. 2012, MNRAS, 427, 146
Hirata, C., & Seljak, U. 2003, MNRAS, 343, 459
Hirata, C. M., Mandelbaum, R., Seljak, U., et al. 2004, MNRAS, 353, 529
Hogg, D. W., & Lang, D. 2013, PASP, 125, 719
Huterer, D. 2010, General Relativity and Gravitation, 42, 2177
Huterer, D., Takada, M., Bernstein, G., & Jain, B. 2006, MNRAS, 366, 101
Irwin, J., & Shmakova, M. 2005, New Astron. Rev., 49, 83
Johnson, N., Kemp, A., & Kotz, S. 2005, Univariate Discrete Distributions, Wiley Series in Probability and Statistics (Hoboken, New Jersey: John Wiley & Sons)
Kacprzak, T., Bridle, S., Rowe, B., et al. 2014, MNRAS, 441, 2528

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    Kacprzak, T., Zuntz, J., Rowe, B., et al. 2012, MNRAS, 427, 2711
Kaiser, N. 2000, ApJ, 537, 555
Kaiser, N., & Squires, G. 1993, ApJ, 404, 441
Kaiser, N., Squires, G., & Broadhurst, T. 1995, ApJ, 449, 460
Kitching, T. D., Balan, S. T., Bridle, S., et al. 2012, MNRAS,423, 3163
Kitching, T. D., Rowe, B., Gill, M., et al. 2013, ApJS, 205, 12
Koekemoer, A. M., Fruchter, A. S., Hook, R. N., & Hack, W. 2003, in HST Calibration Workshop : Hubble after the Installation of the ACS and the NICMOS
Cooling System, ed. S. Arribas, A. Koekemoer, & B. Whitmore,337
Koekemoer, A. M., Aussel, H., Calzetti, D., et al. 2007, ApJS, 172, 196
Lackner, C. N., & Gunn, J. E. 2012, MNRAS, 421, 2277
Lauer, T. R. 1999, PASP, 111, 227
Laureijs, R., Amiaux, J., Arduini, S., et al. 2011, ArXiv e-prints, arXiv:1110.3193
Leauthaud, A., Massey, R., Kneib, J.-P., et al. 2007, ApJS, 172, 219
Long, K. S., Bagett, S. M., Deustua, S., & Riess, A. 2010, in 2010 Space Telescope Science Institute Calibration Workshop- Hubble after SM4.
Preparing JWST, held 21-23 July 2010 at Space Telescope Science Institute. Edited by Susana Deustua and Cristina Oliveira. Published online at
http://www.stsci.edu/institute/conference/cal10/proceedings, p.26
Luppino, G. A., & Kaiser, N. 1997, ApJ, 475, 20
Makinson, D. 2012, Sets, Logic and Maths for Computing, Undergraduate Topics in Computer Science (London: Springer-Verlag)
Mandelbaum, R., Hirata, C. M., Leauthaud, A., Massey, R. J.,& Rhodes, J. 2012, MNRAS, 420, 1518
Mandelbaum, R., Hirata, C. M., Seljak, U., et al. 2005, MNRAS, 361, 1287
37
Mandelbaum, R., Rowe, B., Bosch, J., et al. 2014, ApJS, 212, 5
Massey, R., & Refregier, A. 2005, MNRAS, 363, 197
Massey, R., Stoughton, C., Leauthaud, A., et al. 2010, MNRAS, 401, 371
Massey, R., Heymans, C., Bergé, J., et al. 2007, MNRAS, 376, 13
Massey, R., Hoekstra, H., Kitching, T., et al. 2013, MNRAS, 429, 661
Melchior, P., Böhnert, A., Lombardi, M., & Bartelmann, M. 2010, A&A, 510, A75
Melchior, P., & Viola, M. 2012, MNRAS, 424, 2757

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    Meng, Z., Zhou, X., Zhang, H., et al. 2013, PASP, 125, 1015
Meyers, J. E., & Burchat, P. R. 2014, Journal of Instrumentation, 9, C3037
Miyazaki, S., Komiyama, Y ., Nakaya, H., et al. 2012, in Society of Photo-Optical Instrumentation Engineers (SPIE) Conference Series, V ol. 8446, Society of
Photo-Optical Instrumentation Engineers (SPIE) Conference Series
Moffat, A. F. J. 1969, A&A, 3, 455
Moore, A. C., Ninkov, Z., & Forrest, W. J. 2004, in Society of Photo-Optical Instrumentation Engineers (SPIE) Conference Series, V ol. 5167, Focal Plane Arrays
for Space Telescopes, ed. T. J. Grycewicz & C. R. McCreight, 204–215
Nakajima, R., & Bernstein, G. 2007, AJ, 133, 1763
Navarro, J. F., Frenk, C. S., & White, S. D. M. 1996, ApJ, 462, 563
Noll, R. J. 1976, Journal of the Optical Society of America (1917-1983), 66, 207
Patterson, F. S. 1940, Harvard College Observatory Bulletin, 914, 9
Patterson, T. 1968, Mathematics of Computation, 22, 847
Peacock, J. A., Schneider, P., Efstathiou, G., et al. 2006, ESA-ESO Working Group on “Fundamental Cosmology”, Tech. rep., arXiv:0610906
Pence, W. D., Chiappetti, L., Page, C. G., Shaw, R. A., & Stobie, E. 2010, A&A, 524, A42
Plazas, A. A., & Bernstein, G. 2012, PASP, 124, 1113
Plazas, A. A., Bernstein, G. M., & Sheldon, E. S. 2014, Journal of Instrumentation, 9, C4001
Press, W. H., Teukolsky, S. A., Vetterling, W. T., & Flannery, B. P. 1992, Numerical recipes in C: The art of scientiﬁc computing, 2nd ed. (Cambridge: Cambridge
University Press)
Racine, R. 1996, PASP, 108, 699
Rasmussen, A. 2014, Journal of Instrumentation, 9, C4027
Refregier, A. 2003, MNRAS, 338, 35
Refregier, A., Kacprzak, T., Amara, A., Bridle, S., & Rowe, B. 2012, MNRAS, 425, 1951
Reyes, R., Mandelbaum, R., Gunn, J. E., et al. 2012, MNRAS, 425, 2610
Rhodes, J., Leauthaud, A., Stoughton, C., et al. 2010, PASP,122, 439
Rolland, G., Pinheiro da Silva, L., Inguimbert, C., et al. 2008, Nuclear Science, IEEE Transactions on, 55, 2070
Rowe, B., Bacon, D., Massey, R., et al. 2013, MNRAS, 435, 822

    
    关键要点：
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    Sánchez, E., et al. 2010, Journal of Physics Conference Series, 259, 012080
Schmidt, F., Leauthaud, A., Massey, R., et al. 2012, ApJL, 744, L22
Schneider, P. 2006, in Saas-Fee Advanced Course 33: Gravitational Lensing: Strong, Weak and Micro, ed. G. Meylan, P. Jetzer, P. North, P. Schneider, C. S.
Kochanek, & J. Wambsganss (Berlin: Springer), 269
Schneider, P., van Waerbeke, L., & Mellier, Y . 2002, A&A, 389, 729
Scoville, N., Aussel, H., Brusa, M., et al. 2007, ApJS, 172, 1
Semboloni, E., Hoekstra, H., Huang, Z., et al. 2013, MNRAS, 432, 2385
Sérsic, J. L. 1963, Boletin de la Asociacion Argentina de Astronomia La Plata Argentina, 6, 41
Seshadri, S., Shapiro, C., Goodsall, T., et al. 2013, PASP, 125, 1065
Sheldon, E. S. 2014, MNRAS, 444, L25
van Waerbeke, L. 2010, MNRAS, 401, 2093
Velander, M., Kuijken, K., & Schrabback, T. 2011, MNRAS, 412, 2665
V oigt, L. M., & Bridle, S. L. 2010, MNRAS, 404, 458
V oigt, L. M., Bridle, S. L., Amara, A., et al. 2012, MNRAS, 421, 1385
Wright, C. O., & Brainerd, T. G. 2000, ApJ, 534, 34
Wynne, C. G., Worswick, S. P., Lowne, C. M., & Jorden, P. R. 1984, The Observatory, 104, 23
Zernike, F. 1934, MNRAS, 94, 377
38

    
    关键要点：

> Finished chain.


> Entering new StuffDocumentsChain chain...


> Entering new LLMChain chain...
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    GALSIM是一个模块化的星系图像模拟工具包，由多个国际研究机构的科学家合作开发。该工具包旨在为天文学研究提供高效的星系图像模拟，支持多种天文观测和分析需求。

GAL SIM是一个开源协作项目，旨在为天文学界提供长期有益的图像模拟工具。软件库能够生成包括恒星和星系等天体的图像，支持多种图像处理和高精度操作，如卷积和渲染。GAL SIM的性能满足高精度图像分析需求，适用于当前数据集和未来大型宇宙学调查任务。项目的代码、文档及常见问题解答可在GitHub上找到。关键主题包括数据分析方法、图像处理技术、引力透镜效应和宇宙学观测。

1. 多个地面和空间项目正在进行中，以获取丰富的科学数据，这些项目包括Dark Energy Survey、Hyper Suprime-Cam和Kilo Degree Survey等。
2. 未来的项目如LSST、ESA的Euclid和NASA的WFIRST-AFTA将在2020年代收集大量的星系成像数据。
3. 这些项目属于“Stage III”和“Stage IV”暗能量调查，数据量的增加主要由于调查面积和深度的扩大。
4. 随着调查规模的扩大，减少统计不确定性和系统误差变得更加重要。
5. GAL SIM项目旨在提高从噪声图像中准确估计星系属性的能力。

该内容的关键要点如下：

1. 弱引力透镜技术依赖于从不完美的天体图像中推断天体物理对象的属性，尤其是通过估算星系形状来推导引力剪切。
2. 弱引力透镜可以帮助约束宇宙膨胀和物质结构的增长，因此在检验暗能量和修正引力模型中具有重要价值。
3. 要充分利用该技术，必须将剪切估算中的加性和乘性系统误差控制到非常低的水平（分别为约2×10^-4和2×10^-3）。
4. 这一过程面临诸多技术挑战，包括探测器缺陷、望远镜模糊和失真、以及大气效应。
5. 天文成像数据的模拟对于克服这些挑战至关重要，因为弱透镜估算器在应用于噪声星系图像时常产生系统偏差，除非非常谨慎地构造这些估算器。

1. GREAT08挑战展示了噪声对引力透镜剪切估计方法的影响，推动了对“噪声偏差”的研究和消除。
2. 模型偏差或欠拟合偏差是由于真实星系表面亮度分布与拟合模型不匹配而产生的。
3. GREAT3挑战旨在研究模型偏差对剪切测量方法的影响，并使用哈勃太空望远镜的真实星系图像进行实验。
4. GREAT3还测试了多次曝光成像和点扩散函数（PSF）不确定性对观测数据的影响。
5. GAL SIM的开发是为了生成GREAT3挑战所需的图像。
6. 精确光度测量和形状估计仍面临其他问题，如目标混淆、PSF-目标颜色不匹配、大气色散、星系颜色梯度和非线性探测器效应。

1. 研究表明，模拟研究在剪切测量问题上有助于提高对即将进行的调查的理解。
2. 所有实际的剪切估计器可能存在系统偏差，因此需要通过模拟弱引力透镜观测来校准或控制这些偏差。
3. 高精度的光度测量和天体测量也需要模拟测试，以确保准确性。
4. GAL SIM项目旨在创建一个开源的、经过社区验证的工具包，用于生成必要的图像模拟。
5. 论文结构包括对GAL SIM软件工具包的概述、其组件的详细描述、可表示的天文对象类型、以及“透镜引擎”的功能等。

GAL SIM软件旨在仿真天文图像，具备以下基本功能和需求：

1. 能够灵活表示和生成各种天文对象的模型，包括PSF（点扩散函数）和星系轮廓。
2. 处理坐标转换，如剪切、扩张和旋转，以高精度模拟弱引力透镜效应。
3. 表示对象的卷积，如星系亮度分布与PSF的卷积。
4. 在对象转换、卷积和渲染方面达到Stage IV调查所需的精度。
5. 灵活指定图像像素噪声模型和数据配置，以便在控制测试中评估这些数据属性的重要性。
6. 能够针对星系或PSF模型执行上述所有操作。

此外，文中也提到软件的部分实现细节和性能测试结果，以及当前版本不支持的某些真实数据效果。

1. 该软件用于模拟弱引力透镜观测，精确的天文测量和光度测量。
2. GAL SIM 项目强调软件设计和实现，采用开源许可（BSD风格），使用Python和C++编写。
3. 软件设计为模块化，便于扩展和协作开发。
4. 提供清晰的文档和示例脚本，帮助用户学习和使用。

1. 新代码必须附带测试套件才能合并到主代码库，确保代码经过全面测试。
2. 单元测试有助于解决跨平台兼容性问题，并在多种系统上运行。
3. 新代码需经过开发团队的详细代码审查，包括代码、文档和单元测试的审查。
4. 使用GitHub的“Pull Request”功能进行代码审查，帮助发现并修正错误。
5. GAL SIM是一个模块化的Python类库，旨在为天文图像模拟提供灵活的工具。
6. 提供独立的可执行文件，允许用户通过配置文件使用GAL SIM功能。

关键要点：

1. 每个教程示例脚本都有对应的配置文件，可以生成相同的输出文件。
2. GAL SIM 工具包的类和函数按功能分为几类，包括表示天文对象、生成引力透镜畸变、图像坐标与世界坐标的连接、渲染图像、生成随机数并应用噪声、估计对象形状等。
3. 实用工具的使用信息可在 GAL SIM 项目页面的在线文档中找到。
4. Python 是 GAL SIM 的主要用户界面，但许多数值计算在 C++ 中实现。
5. 文章重点在于 GAL SIM 类和函数生成的输出的科学理论描述及其准确性验证。

1. `demo12` 目前没有对应的配置文件，计划在不久的将来添加此功能。
2. GalSim 提供了示例脚本和快速参考指南作为文档的起点，还有 Python 函数和类方法的文档字符串。
3. GAL SIM 中的表面亮度分布模型包括指数盘和德瓦夸勒轮廓。
4. 指数盘轮廓适用于描述螺旋星系的外部区域，其亮度公式与总通量、尺度半径和半光半径相关。
5. 德瓦夸勒轮廓适用于椭圆星系和星系中心区域，其亮度公式也与总通量、尺度半径和半光半径相关。

1. de Vaucouleurs和Sérsic光谱描述星系表面亮度分布。
2. de Vaucouleurs光谱在标度半径处呈尖峰，但具有非常宽的翼。
3. Sérsic光谱是指数型和de Vaucouleurs光谱的推广，其表面亮度公式涉及参数\( n \)，且支持用\( r_0 \)或半光半径来表征大小。
4. GAL SIM软件中提供截断选项，可在给定半径后将表面亮度降至零。
5. Sérsic光谱的\( n \)值允许从0.3到6.2变化，因而其适用性更广泛。

1. 星系剖面：通过HST拍摄的高分辨率星系图像，可直接用作模拟的光剖面模型。这些图像包含真实的形态变化和不规则性，尤其对于高红移星系群体至关重要。GAL SIM工具中使用RealGalaxy类表示这些剖面。

2. 恒星和PSF模型：由于望远镜的有限圆形孔径，光将产生衍射图案，形成中央亮峰及环形结构。为解释这一现象，引入Airy和遮挡Airy剖面模型，以Airy函数和Bessel函数描述。若孔径中有遮挡，衍射图案则包含遮挡因子的修正，在GAL SIM中由Airy类表示。

1. Zernike多项式常用于逼近入射在圆形光瞳上的复杂像差波前。
2. Noll(1976)的惯例用于标记这些多项式，通过整数j表示，并可以用n和m来定义。
3. 低阶Zernike多项式对应于常见的望远镜像差，如焦散、像散和彗差等。
4. Zernike多项式提供了一个简便而紧凑的望远镜像差近似模型。
5. 在菲涅耳衍射极限下，PSF通过光瞳波前的自相关傅里叶变换计算得出。
6. GAL SIM中的OpticalPSF类用于表示该结果，并提供多种设定选项。 
7. GAL SIM支持到Noll指标j=11的像差，并计划允许任意阶次的Zernike项。

1. **Optical PSF Implementation**: In GAL SIM, the Optical PSF is implemented by creating a real-space image using Discrete Fourier Transform and then interpolating it with the InterpolatedImage class.

2. **Moffat Profile**: Developed by Moffat (1969), this profile models stellar PSFs with broader wings than a Gaussian, providing a better fit to observations. It is characterized by parameters such as total flux (F), scale radius (r0), and a shape parameter (β), which typically ranges from 2 to 5. In GAL SIM, it is represented by the Moffat class, with size specified by r0, FWHM, or half-light radius, and can be truncated.

3. **Kolmogorov Profile**: This profile models PSFs based on the Kolmogorov spectrum of atmospheric turbulence, providing a better fit for long exposure observations than the Moffat profile. Its surface brightness is defined in Fourier space, with parameters including total flux (F) and the Fried parameter (r0), which typically ranges from 10 to 20 cm.

1. Fried参数\( r_0 \)与波长关系为\( r_0 \propto \lambda^{-6/5} \)，并用于GAL SIM中的Kolmogorov类。
2. 高斯轮廓具有解析性，在真实和傅里叶空间均较紧凑，适用于简单模拟及测试。通过线性叠加，高斯轮廓可接近真实轮廓。
3. 高斯轮廓的表面亮度公式为\( I(r)= \frac{F}{2\pi\sigma^2}e^{-r^2/2\sigma^2} \)，在GAL SIM中由Gaussian类表示。
4. Shapelets由Bernstein＆Jarvis和Refregier独立开发，用于刻画紧凑表面亮度轮廓。它们由二维高斯轮廓乘以多项式构成，为完整基函数集合，但对某些轮廓的分解可能不切实际。

1. Shapelet分解提供了一种紧凑的方式来表示接近高斯分布的图像，通过低阶修正描述图像中的大部分信息。
2. GAL SIM中的Shapelet类遵循Bernstein & Jarvis (2002)的符号，与Massey & Refregier (2005)提出的“极坐标形状元”相似。
3. Shapelet扩展由两个索引p和q定义，形状元函数是二维量子谐振子的特征函数。
4. 形状元的傅里叶变换也是形状元，使得在傅里叶空间中卷积形状元非常高效。
5. 在某些情况下，可以将图像作为表面亮度分布进行处理，需要在像素值之间进行插值。
6. 直接观测个体星系的图像可以用于进一步的模拟。
    
    关键要点：

> Finished chain.

> Finished chain.


> Entering new StuffDocumentsChain chain...


> Entering new LLMChain chain...
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    关键要点：

1. 光学点扩散函数（PSF）过于复杂，无法进行解析建模，因此使用OpticalPSF类通过插值在有限网格上进行评估。
2. InterpolatedImage类将任意n×n图像数组转换为连续的表面亮度分布。
3. 不同的插值核（如delta函数、sinc核、立方和五次多项式插值、Lanczos核）在渲染过程中有不同的计算复杂度和适用性。
4. 高阶插值核在模拟中提供了性能和精度的良好平衡。
5. GAL SIM可以对表面亮度分布进行各种变换，以表示椭圆形或偏心的亮度分布。

1. 可以通过因子缩放、总通量调整来改变剖面的整体幅度，新剖面定义为 I′(x) = cI(x)。
2. 使用任何一一对应的平面变换 T，对图像进行变换，表示为 I′(x) = I[T⁻¹(x)]。
3. GAL SIM 提供了 transform 操作，实现由矩阵 A 定义的局部线性变换，包括任意失真、旋转、反向翻转或坐标系统扩展。
4. 用户可直接指定矩阵 A，或使用特定的 GAL SIM 操作如旋转、扩展、放大、剪切和镜头。
5. dilate 命令可以在保持通量不变的情况下扩展线性尺寸，这是一种常见操作的便捷函数。
6. shift 函数可以将剖面按数量 x0 平移。
7. shift 和 transform 结合可以实现任意仿射变换。
8. 表格展示了插值方法及其特性，如 Delta、Nearest、Linear、Cubic 等。

1. 独立的封装对象用于与原始轮廓接口，便于集中实现变换代码，减少重复，提高可靠性。

2. GAL SIM目前不支持对单个轮廓进行非仿射变换，但可以通过局部线性逼近处理整个图像的坐标变换。

3. 可以通过加法操作将两个或多个亮度轮廓合并，并用Convolve函数实现多个对象的卷积。

4. AutoConvolve和AutoCorrelate函数可提高计算效率，分别用于对象自身卷积和180°旋转卷积。

5. GAL SIM支持反卷积，通过Deconvolve函数在傅里叶空间求逆，需与其他轮廓卷积以获得可渲染结果。

6. 常见用例包括通过反卷积处理观察图像。

1. GAL SIM的重卷积算法可以将天文图像从一个望远镜的PSF转换为另一个望远镜的PSF，同时调整像素尺度。
2. 为避免图像伪影，新的PSF的空间频率必须低于原始PSF。
3. GAL SIM支持模拟波长依赖的天体对象，通过定义表面亮度和波长的函数关系。
4. Chromatic类结合了无色轮廓和光谱能量分布（SED），允许创建具有复杂波长依赖形态的星系。
5. Chromatic对象可以进行变换、相加和卷积，支持不同波长的变换函数。
6. GAL SIM提供了ChromaticAtmosphere函数，用于模拟大气PSF中的色差折射和色差变化。

1. GAL SIM工具包是一个用于未来研究的资源，能够模拟宇宙学中许多重要的波长依赖效应。
2. GAL SIM的主要用途是生成模拟图像，以测试弱引力透镜数据分析算法。
3. 在弱引力透镜的情况下，透镜剪切和会聚的模拟框架是关键。
4. 透镜剪切（γ1和γ2）描述了星系图像的各向异性拉伸，而透镜会聚（κ）描述了视大小的各向同性变化。
5. 即使κ=0，弱透镜剪切通常也不保面积，GAL SIM提供了保面积的剪切变换选项。
6. GAL SIM可以对对象应用单一的透镜剪切和会聚值。

1. GAL SIM可以生成与两种物理场景相关的剪切和会聚场：宇宙学弱透镜场和球形NFW晕引起的弱透镜。
2. 宇宙学透镜场通过高斯随机场近似模拟，主要用于测试测量算法，而非精确的宇宙学参数确定。
3. 用户可以使用更真实的宇宙射线追踪模拟输出，以创建包含真实剪切和会聚场的星系形状目录。
4. GAL SIM能够处理E-和B-模式剪切功率谱，并生成相应的随机剪切和会聚场。
5. 剪切在网格上生成，但可以通过插值在网格内任意位置进行计算。

关键要点如下：

1. 使用矢量连接成对星系的角分离定义相关函数ξ±(θ)，与E模和B模的平坦天空功率谱相关。

2. 在宇宙学剪切相关中，B模的影响通常可以忽略，但高阶效应可能引入实质性的B模。

3. 生成剪切数据时有必要包括B模，比如绘制大气PSF各向异性需要相似数量的E和B功率。

4. 功率谱P E 和P B 具有角度的平方的维度，且可接受多种格式和单位输入。

5. 定义依赖于连续傅立叶变换，但实际中使用离散傅立叶变换（DFT），需注意DFT的约定。

6. 根据输入空间网格计算的最小和最大一维波数来确定功率P(k)，并返回到实空间以获得剪切场。

1. 在平面天空极限下，球谐函数的功率谱可以用波数和功率谱来替代。
2. 使用NUMPY进行傅里叶变换时，需要考虑输入网格配置的归一化因子。
3. 基于DFT的算法在生成剪切时受限于有限的波数范围和离散与连续傅里叶变换的差异。
4. GAL SIM提供选项来调整网格以减少剪切功率的丢失，但可能导致功率谱的变化和E、B模式泄漏。
5. GAL SIM有工具预测有限波数范围对剪切相关函数的影响，帮助用户评估网格选择的适用性。

1. 为避免混叠，GAL SIM的剪切生成程序可以在Nyquist尺度处对输入功率谱进行硬或软截止。
2. 在网格上生成剪切和会聚后，用户可以将其插值到网格内的任意位置，但需注意避免插值过程对剪切功率谱或相关函数的误导性修改。
3. 插值会显著修改剪切的二点函数，尤其是在小于原始网格间距三倍的尺度上，因此选择网格间距时需谨慎。
4. NFWHalo类可以生成符合球形NFW剖面的暗物质晕的剪切和会聚，计算依赖于假设的宇宙学模型。
5. NFW透镜晕由质量、集中度、红移和图像中的位置定义，可以根据源星系的位置和红移计算相应的透镜量。

1. GAL-SIM采用观测到的星系坐标系，没有考虑或应用光偏转角度，这对某些研究（如星系团的放大效应）可能有影响。
2. 星系模型通常定义在天空的角度单位上，需要将像素坐标与天空坐标（世界坐标）进行匹配。
3. 世界坐标系统（WCS）可以是简单的像素比例或更复杂的函数，通常在FITS数据文件头中找到。
4. GAL-SIM支持两种基本的WCS类型：天球坐标系（基于赤经和赤纬）和欧几里得坐标系（基于天球的切平面投影）。

1. 在GAL SIM中，坐标系统通过EuclideanWCS的子类表示，最通用的是UVFunction，可以表示用户提供的任意函数。
2. AffineTransform是最通用的统一坐标变换，所有像素大小和形状相同，但形状可以是任意平行四边形。
3. PixelScale是AffineTransform的简单特例，描述了统一的正方形像素，常用于剪切测量方法的模拟测试。
4. GAL SIM允许用户忽略复杂的WCS选项，仅使用像素比例参数。
5. 将表面亮度分布从天空坐标转换为图像坐标相对简单，假设WCS函数的一阶导数在对象大小范围内近似常数。
6. 当前，GAL SIM无法准确处理在对象大小范围内显著变化的变换。
7. 处理天体坐标系统时，首先在对象位置进行局部切线投影，使用TAN投影。

1. Calabretta & Greisen (2002) 提到的切平面投影可以转换为局部欧几里得坐标系。
2. 计算物体位置的WCS雅可比矩阵，以定义局部仿射近似。
3. 在GAL SIM中应用雅可比变换，从(u,v)转换到(x,y)，需要使用J的逆矩阵，并乘以|detJ|以保持总通量。
4. GAL SIM WCS类有函数toImage和toWorld，用于双向转换。
5. 处理复杂WCS时需注意像素响应和PSF轮廓在不同坐标系中的定义。
6. 忽略PSF时，展示如何在图像中处理均匀方形像素上的星系。

1. 图像坐标中的剖面通过积分得到相同的总光通量。
2. 在两种坐标系中，像素响应由具有单位光通量的二维顶帽函数表示。
3. 星系表面亮度分布在图像上以像素面积进行积分，积分结果是星系剖面与像素响应的卷积。
4. 卷积可在任何一个坐标系中进行，并由GAL SIM软件自动处理。
5. 处理PSF时，要注意其定义所用的坐标系特别在使用复杂的WCS时。

1. 像素失真与大气和望远镜光学引起的光学传输函数(PSF)有关，选择失真坐标时需注意PSF的定义坐标。
2. 如果PSF在图像坐标中定义，需要转换为世界坐标后再与星系分布进行卷积。
3. 从图像测量的PSF已包含像素响应卷积，模拟数据时不应重复像素卷积，以避免双重像素响应。
4. 在GAL SIM中，有三种图像渲染方法：直接绘制、离散傅里叶变换(DFT)、光子射击。
5. 三种渲染方法原则上应相等，但光子射击方法有固有的噪声差异，并自动像素化。
6. 使用no_pixel选项时，将采用直接绘制或DFT来渲染图像。

1. 不同渲染方法间存在因技术近似而导致的细微差异。
2. 并非所有对象都可以用三种方法渲染。例如，实空间卷积仅用于两个轮廓的卷积，且需一个为像素响应。
3. 反卷积仅通过DFT方法实现，非仿射变换如弯曲不能在傅里叶空间中进行，并未在GAL SIM中实现。
4. 直接渲染是GAL SIM中对象绘制的默认方式，通过与方形像素卷积实现对象表面亮度的积分。
5. 可以选择不卷积像素，直接采样像素中心的表面亮度。
6. 如果使用解析对象而不卷积像素响应，GAL SIM会采用直接渲染，仅需计算每个输出像素处的亮度值。
7. 许多对象在实空间有解析公式，因此直接渲染简单，但例如Kolmogorov轮廓仅在傅里叶空间有解析表示。
    
    关键要点：

> Finished chain.

> Finished chain.


> Entering new StuffDocumentsChain chain...


> Entering new LLMChain chain...
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    1. Hankel变换的计算一次性进行，并在首次创建Kolmogorov对象时保存，以后无需重复。      
2. 通过利用径向对称性的已知特性可以加速计算，通常还可以使用向量化技术提高效率。      
3. Shapelet函数并非径向对称，但其渲染代码使用快速递推关系实现。      
4. 表中列出不同渲染方法的特性及操作复杂度：直接实空间、傅立叶空间、光子射击。      
5. 不同方法在处理卷积、逆卷积及应用变换时有所不同，各有优缺点。      
6. 分析了不同解析GAL SIM对象的特点及其在不同空间中的表示方式。

1. "LUT"指的是需要预先计算并存储在三次样条查找表中的积分函数。
2. 光子发射方法包括“解析法”、“区间法”和“未实现”。
3. 带有遮挡的Airy函数的傅里叶表示法过于复杂，无法用于表格。
4. 对于一般的β值，使用查找表；但对于某些特定的β值，GAL SIM使用解析傅里叶空间公式。
5. 插值图像通常是最慢的直接渲染方法。
6. 变换应用简单，涉及对原始轮廓的变换。
7. 组合渲染可以通过单独渲染每个轮廓并累加其光通量来实现。
8. 卷积通常通过DFT或光子发射方法进行，但在某些情况下可能直接通过高斯-克龙罗德-帕特森积分评估进行。

1. 对于具有硬边缘的两个物体进行卷积时，直接积分方法通常更快且更精确。
2. 在渲染卷积图像（包括像素响应和其他如PSF的分布）时，GAL SIM默认使用离散傅里叶变换（DFT）。
3. 为避免混叠，采样表面亮度分布时，需在输出网格的奈奎斯特频率内。
4. 真实望远镜产生的图像是带限的，超过特定空间频率的部分被滤除。
5. 空基观测通常在接近奈奎斯特尺度进行采样，而地基观测的PSF通常较大，需要适当近似以提高速度。

1. 傅里叶变换在选定的 \( k_{\text{max}} \) 之外为零，这称为图像的带限。
2. 常见的点扩散函数（PSF）如高斯、Moffat和Kolmogorov函数在 \( k \) 上是无界的，因此需要选择一个合适的 \( k_{\text{max}} \) 来近似。
3. GAL SIM 中的每种表面亮度分布都能计算并返回其 \( k_{\text{max}} \)，即傅里叶域分布降到峰值的 \( 10^{-3} \) 以下的 \( k \) 值。
4. 离散傅里叶变换（DFT）的输出值是实际函数在周期 \( P = M \Delta x = 2\pi/\Delta k \) 上的折叠结果。
5. 为了减少折叠导致的误差，DFT 应在足够大的周期上进行，GAL SIM 知道每个分布的 \( k_{\text{step}} \) 值。
6. 如果用户请求的图像不符合此标准，GAL SIM 会在更大的网格上执行 DFT，并从中提取输出图像。
7. DFT 图像的维度必须满足 \( M \geq 2k_{\text{max}}/k_{\text{step}} \)。
8. 某些 GAL SIM 分布包含尖锐特征，可能导致所需的最小 \( M \) 超过最大允许的 DFT 大小，GAL SIM 会在这种情况下抛出错误。

1. 在渲染真实图像时，通过与点扩散函数（PSF）和像素响应的卷积来限制图像的带宽。
2. GAL SIM可以对某些径向轮廓进行快速的傅里叶域解析计算。
3. 对于没有快速解析公式的径向轮廓，使用数值变换和三次样条插值来计算傅里叶域值。
4. 在小k值时，用解析的二次或更高阶泰勒展开替代样条插值，以确保弱引力透镜测量的准确性。
5. Shapelet轮廓在傅里叶空间的绘制与直接渲染相同，使用快速递归关系。
6. 对于插值图像，需要在DFT值网格之间进行k空间插值，并考虑插值图像的有限范围。

1. 周期函数的变换需要两个不同的插值器：用户选择的x域插值器\(K_x\)和用于频域上的k域插值器\(K_k\)。
2. 正确评估频域上的插值功能很复杂，Bernstein & Gruen（2014）展示了详细步骤。
3. 理论上正确的k域插值器形式是sinc函数，但计算复杂，因此通常使用紧凑插值器来近似\(K_k\)。
4. 插值可能导致图像的轻微缩放和“鬼影”现象，但通过零填充和自定义插值器可以将这些影响降到很低。
5. GAL SIM中默认采用该方法进行傅里叶域渲染，但用户可以调整零填充和插值器。
6. 插值会扩展对象支持域，因此需要调整频域采样步长\(kstep\)。

1. **Sinc插值器的影响**：Sinc插值器会显著扩展图像的影响范围。对于原始采样图像，\(k_{max}\)是无限的，但应用插值器后，\(k_{max}\)变为\(c\pi/\Delta x\)，其中\(c\)是插值器的特征常数。Sinc插值器理想情况下\(c=1\)，而Lanczos插值器（\(n=3-5\)）提供更紧凑的支持，\(2 < c < 3\)即可。

2. **变换的傅里叶域对应**：函数的平移和线性变换在傅里叶域有对应关系。平移不改变\(k_{max}\)和\(k_{step}\)，而线性变换会影响这两个值。

3. **傅里叶变换的线性性质**：对于多个成分的组合，\(k_{max}\)取各成分的最大值，\(k_{step}\)取最小值。

4. **卷积的影响**：卷积在傅里叶域中是乘积关系，\(k_{max}\)取各成分的最小值，\(k_{step}\)的计算是启发式的，基于对象的中心二阶矩在卷积下的平方和。

5. **启发式方法的局限性**：对于非高斯分布，\(k_{step}\)的传播规则仅在高斯情况下被认为是正确的。

1. 在卷积过程中，对于严格紧凑的函数，最大非零元素线性增加，而不是以平方和的方式增加。
2. GAL SIM提供了手动增加DFT大小的选项，以减少过度混叠的风险。
3. 在傅里叶域中，应用反卷积操作会产生1/˜IA (k)，通常需要重新卷积以避免不良定义。
4. 光子射击技术被用于生成模拟图像，GAL SIM扩展了该技术以支持几乎所有对象。
5. 光子射击允许非均匀权重，以便表示负的表面亮度值，这对于实现带有负区域的插值是必要的。
6. 光子射击要求对象能够报告正负区域的通量绝对值，并根据这些值分配光子权重。

1. 负亮度区域会导致光子总通量的变化，GAL SIM 会自动选择适当的光子数量来正确处理噪声。
2. 正负通量光子之间的部分抵消导致噪声分布略微偏离精确的泊松分布，虽然其方差近似准确。
3. 仅由正通量轮廓构建的对象不存在这种影响，噪声确实是泊松分布。
4. 在某些情况下，|w i|可以略微偏离常数fabs/Nγ值，影响噪声特性。
5. 对于解析对象，通过从单位正方形或圆进行已知变换来实现光子投射函数I(x)最为简单。
6. 多种轮廓是圆对称函数，使用累积径向分布函数实现。
7. 对于高斯和Moffat类，GAL SIM 使用快速解析函数。
8. 其他圆对称轮廓使用特定算法将均匀偏差转换为径向通量分布。

1. 使用标准数值积分技术计算每个环形区域的绝对通量。
2. 算法需要设定最大半径，因此进行光子射击渲染时需要截断无限的轮廓。
3. 通过插入节点和递归剖分径向间隔来计算绝对通量，并根据设定的阈值决定是否继续分割。
4. 计算每个环形区域的绝对通量积分和光子射入该区域的概率，以及光子位于内部的累积概率。
5. 根据概率分布来选择光子的位置，使用“婚礼蛋糕”模型从固定值的环形区域分布近似|I(r)|.
6. 若光子处于亮度变化小的区域，重新权重光子；若变化大，使用拒绝采样法进行光子选择，以确保准确度。

1. 光子的方位角通过统一偏差选择。
2. 光子位置和权重的计算需要2Nγ(1+ǫ)个统一偏差和Nγ(1+ǫ)次I(r)的评估，其中ǫ是被拒绝的光子的比例。
3. 环带的有限宽度应足够小，以保证近似的准确性。
4. 为优化区间选择，区间被重新组织成一个二叉树。
5. 特定的光子投射算法用于Sersic、Exponential、DeVaucouleurs、Airy和Kolmogorov类。
6. 在Exponential和DeVaucouleurs配置文件中，区间结构和通量积分只构建一次。
7. Shapelet对象由于非径向对称性，未实现光子投射支持。
8. 对于插值图像对象，光子投射需要将光子分配到网格点，并创建累积概率。

这是内容概要，希望能帮到你！

1. 在光子发射过程中，图像的插值通过将每个光子的位移从插值核中抽取来实现。
2. 2D插值器可分解为1D函数，允许分别从x和y方向抽取位移。
3. 对于某些插值器，光子发射需要额外的随机偏移和核函数评估。
4. 图像变换和组合在光子发射中实现简单，包括通量重缩放和平面变换。
5. 多个轮廓的光子发射通过多项式分布确定每个轮廓的光子数量，并将结果合并。
6. 卷积通过从两个输入分别发射光子并随机化顺序来避免位置相关性。

1. GAL SIM不能使用光子发射方法对包含反卷积的任何轮廓进行处理。
2. 光子发射方法的主要优点是，针对低信噪比（S/N）的对象，发射较少数量的光子比进行一次或多次傅里叶变换要快。
3. 理想情况下，目标的光子数等于相机检测到的光子数，但是由于光子数是随机变量，使用Poisson统计学来估计总数。
4. 当需要发射负光子时，更复杂的情况出现，这时需要发射更多的光子来保持正确的总通量，同时增加的数量会导致更多的噪声。
5. 解决方案是每个光子携带较少的通量，并使用更多的光子发射。
    
    关键要点：

> Finished chain.

> Finished chain.


> Entering new StuffDocumentsChain chain...


> Entering new LLMChain chain...
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    1. 每个光子携带的流量为±g，目标是使总流量和方差等于期望流量f。
2. 通过公式计算得到g = 1 - 2η和N photons = f/(1-2η)²。
3. GAL SIM的drawImage函数默认执行上述计算，但用户可以选择设置不同的光子数量。
4. 计算假设η在整个轮廓上是常数，但实际上η不是常数，导致不同区域的光子图像之间存在相关性。
5. 噪声模式类似于真实光子图像的噪声，但不应依赖于噪声的稳定性或无相关性，且像素噪声不遵循泊松统计。
6. 当η接近0.5时，这些不准确性更加明显。
7. 对于受天空背景光主导的中等高流量物体，可以通过发射较少的光子（每个光子的流量大于g = 1 - 2η）来实现相同的信噪比，从而节省计算成本。

1. 每个像素的泊松噪声允许有额外的方差 \(\nu\)，最亮像素的方差可达 \(I_{\text{max}} + \nu\)。
2. 光子数量可以减少至 \(I_{\text{max}} / (I_{\text{max}} + \nu)\)，每个光子的光通量增加以保持总光通量 \(f\) 不变。
3. 这种方法在图像受天空噪声主导时有效，常用于模拟地面观测。
4. 使用 GAL SIM 的用户需明确每个像素可容忍的额外噪声 \(\nu\)，通常为每像素天空噪声的 1%。
5. 算法需先估计 \(I_{\text{max}}\)，然后根据公式 (63) 和 (64) 调整光子数量和光通量。
6. 图像渲染算法在速度和准确性之间存在权衡，用户可通过 GSParams 结构调整参数以适应不同需求。

关键要点：

1. **folding_threshold**：限制由于DFT周期性导致的图像折叠，确保图像大小足够大以避免过多的通量丢失。默认值为5.e-3。

2. **maxk_threshold**：设定在傅里叶空间中被排除的高频模式的最大幅度，以减少图像中的“振铃”效应。默认值为1.e-3。

3. **xvalue_accuracy和kvalue_accuracy**：分别设定实空间和傅里叶空间值的精度，确保近似误差不超过总通量的指定倍数。默认值为1.e-5。

4. **realspace_relerr和realspace_abserr**：设定实空间卷积的相对和绝对误差容限，确保每个像素的通量误差在指定范围内。默认值分别为1.e-4和1.e-6。

5. **shoot_accuracy**：设定光子发射时总通量的相对精度，限制算法近似导致的通量误差。

1. `shoot_accuracy`参数的默认值为1.e-5，可以通过`gsparams`在初始化对象时设置为非默认值。
2. GAL SIM软件可以进行“重卷积”处理，以模拟低分辨率望远镜观测到的真实星系图像。
3. 重卷积条件是目标波段限制与原始HST波段限制相关，适用于弱透镜效应。
4. `RealGalaxy`类表示去卷积后的HST星系，可以进行变换并与最终PSF卷积。
5. HST COSMOS调查的星系观测数据可从GAL SIM库下载。
6. 输入图像需要进行噪声填充，GAL SIM软件在数值验证中对填充量进行了广泛测试。
7. 实现相比SHERA软件有所更新。

关键要点：

1. **插值技术的不同**：SHERA只实现了三次插值，而GAL SIM提供了多种可调插值选项。

2. **PSF解卷积方法**：GAL SIM完全解卷积原始HST PSF，而SHERA使用伪解卷技术，仅在低分辨率图像可访问的尺度上解卷积。不过，主要影响是渲染剪切星系的准确性。

3. **处理相关噪声**：HST图像含有相关噪声，剪切和卷积过程会引入更多相关性。GAL SIM能够在整个重卷积过程中模拟这些噪声，并将最终渲染图像处理为仅含不相关的高斯噪声。

4. **噪声模型**：GAL SIM提供多种随机噪声模型用于模拟图像，包括处理光子射击图像的泊松分布噪声和DFT渲染图像所需的附加噪声。

5. **随机偏差实现**：所有GAL SIM的噪声模型都基于从各种概率分布中采样的随机偏差实现，包括均匀分布和高斯分布。

1. Poisson分布（Pois(λ)）在GAL SIM中用于噪声模型，也用于大规模模拟中生成随机变量。
2. 其他分布在模拟中较有用，包括二项分布、Gamma分布、Weibull分布（指数和Rayleigh分布的扩展）以及χ²分布。
3. GAL SIM支持从用户提供的任意概率分布函数中采样，利用DistDeviate类实现。
4. 多数噪声模型生成不相关噪声，GaussianNoise类添加N(0,σ²)的高斯噪声。
5. PoissonNoise类为每个像素添加Pois(λi)的泊松噪声，λi是像素的平均计数，不是空间平稳的。
6. CCDNoise类模拟正常CCD图像噪声，包括Poisson噪声和空间平稳的高斯读出噪声，并可指定增益值。

1. **噪声类型**：
   - Poisson噪声影响光子计数，图像以ADU表示。
   - VariableGaussianNoise类实现非平稳高斯噪声模型，为每个像素添加不同方差的噪声。
   - DeviateNoise类使用随机偏差为基础，为每个像素独立添加噪声。

2. **相关噪声**：
   - 天文图像可能包含空间相关噪声，可能由探测器串扰或像素校正引起。
   - 合并多张图像可能导致显著的相关噪声。

3. **HST图像**：
   - Drizzled HST图像由于单个输入像素的通量分配给多个输出像素，常出现相关噪声。
   - HST COSMOS调查图像包含显著的像素间噪声相关性。

4. **相关高斯噪声统计**：
   - 相关高斯噪声的统计特性由协方差矩阵描述。
   - 像素噪声自相关函数用于定义噪声场的统计特性。

1. 物理噪声函数 \(\xi_{\text{noise}}[n,m]\) 具有二重旋转对称性，并在 \(n = m = 0\) 处达到峰值。
2. 如果噪声是平稳的，其方差和协方差不依赖于图像中的位置，则 \(\xi_{\text{noise}}[n,m]\) 完全决定图像中所有像素对的协方差矩阵。
3. 噪声功率谱 \(P_{\text{noise}}[p,q]\) 是 \(\xi_{\text{noise}}[n,m]\) 的傅里叶对应物，可用于生成高斯随机噪声场。
4. 通过逆离散傅里叶变换（DFT）生成实值噪声场 \(\eta[n,m]\)，并利用 Hermitian 对称性提高计算效率。
5. 在 G AL SIM 中，使用 CorrelatedNoise 类来建模和生成平稳相关噪声，内部通过 2D 分布表示噪声相关函数。

1. **生成高斯随机场**：通过逆离散傅里叶变换（DFT），可以使用CorrelatedNoise类生成具有任意物理功率谱或相关函数的高斯随机场。

2. **噪声转换和组合**：CorrelatedNoise类利用GAL SIM的表面亮度分布来描述相关函数，使得噪声的转换和组合变得简单。多个噪声场可以相加，结果是各个噪声相关函数的总和。

3. **卷积处理**：噪声模型的卷积与表面亮度的处理不同，噪声应与核的自相关进行卷积。

4. **离散相关函数的描述**：在R²中描述离散相关函数ξnoise[n,m]，需要考虑像素的有限大小，特别是在图像用于形成不同尺度的星系模型时。

5. **连续空间变量表示**：希望将ξnoise[n,m]表示为连续空间变量ξnoise(x,y)，以便在像素尺度s下满足ξnoise(ns,ms)=ξnoise[n,m]。

6. **像素响应模型**：图像中的噪声可视为像素中心的δ函数样本与像素响应的卷积，ξnoise(x,y)的值应在像素边界处不连续变化。

1. 处理如卷积等操作时，像素边界的锐利不连续性使得Fourier空间表示非常不紧凑，耗费大量存储和计算资源。

2. 为降低计算成本，GAL SIM采用双线性插值法在采样值之间定义连续函数，以处理相关的高斯噪声。

3. 插值法对计算效率的影响通常较小，尤其在处理来自银河观察的模型噪声时，最终图像的像素尺度通常大于输入图像的像素尺度。

4. 提供的HST COSMOS星系图像由于“drizzling”技术导致噪声空间相关，GAL SIM下载的图像工具用于RealGalaxy类处理这些噪声。

1. 研究估算了COSMOS F814W图像中的像素噪声相关函数，选取了约100个不含检测到目标的矩形区域进行分析。
2. 这些区域通常为边长50-200像素的正方形，计算得出的平均噪声相关函数用于GAL SIM软件的星系模型。
3. 噪声美白技术用于处理由重卷积算法导致的剪切与相关噪声，以减少模拟中由噪声导致的系统偏差。
4. 对于高信噪比和低信噪比星系，相关噪声会影响弱透镜效应剪切校准精度，因此在高精度剪切模拟中不能忽视。

关键要点：

1. 图像中存在相关的高斯噪声记为 \(\eta\)，假定其均值为0，并假设其在图像中是平稳的，其协方差矩阵由相关函数或功率谱决定。

2. 添加额外的用于“漂白”的噪声 \(\eta_{\text{whitening}}\)，使得总噪声场为 \(\eta_{\text{total}} = \eta + \eta_{\text{whitening}}\)。

3. \(\eta_{\text{whitening}}\) 的统计属性也由其功率谱 \(P_{\text{whitening}}[p,q]\) 决定，且要求 \(P_{\text{whitening}}[p,q] \geq 0\)。

4. 总噪声场的功率谱为 \(P_{\text{total}} = P_{\text{noise}} + P_{\text{whitening}}\)，可以通过将 \(P_{\text{total}}\) 设为常数使其变得不相关。

5. 选择 \(P_{\text{whitening}}[p,q] = \text{max}_{p,q} \{P_{\text{noise}}[p,q]\} - P_{\text{noise}}[p,q]\) 满足白噪声条件。

6. 实践中，GAL SIM 添加了一小额外方差 \( \epsilon = 0.05 \)，确保 \(P_{\text{whitening}}[p,q] > 0\)，以规避数值舍入误差。

7. 通过添加额外的漂白噪声，可以将相关噪声转换为不相关的白噪声。
    
    关键要点：

> Finished chain.

> Finished chain.


> Entering new StuffDocumentsChain chain...


> Entering new LLMChain chain...
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    关键要点：

1. 研究了COSMOS F814W空白天空图像中的噪声相关性，并进行了噪声标准化。
2. 两个方向的噪声相关性（∆y = 0 和 ∆x = 0）被展示在左侧和右侧面板中。
3. 在一个400×300像素的空白天空区域中进行了噪声美白处理，降低了像素间的协方差。
4. 通过应用§7.5中的方法和公式，将噪声相关性减少了2-3个数量级，使其在大多数情况下变得不可检测。
5. 噪声美白提高了图像的总体方差，但降低了有效信噪比，影响了对象属性（如通量和形状）估计。
6. 噪声美白涉及增添随机噪声，会使图像的最终噪声场方差大于原始图像。

关键要点：

1. 对图像进行去色噪声处理的效果，与图像中对象大小和相关噪声性质有关。
2. 去色噪声后，图像中对象特性的信噪比下降程度小于预期。
3. 噪声去色过程中信息损失量依赖于对象特性、对象轮廓和原始图像中的噪声相关性。
4. 经剪切、PSF卷积后再用大像素尺度渲染的噪声场，去色噪声所需的噪声通常较少。
5. 噪声剪切和卷积会增加大尺度噪声相关性。
6. 使用较大像素尺度和宽PSF卷积会显著降低噪声方差，类似于平滑处理。
7. 在图像生成中，这些效应组合减少了去色噪声的需求。
8. GAL SIM的Image类提供了whitenNoise方法，应用上述去色算法。

1. 提供了两种处理噪声的方法：whitenNoise和symmetrizeNoise，后者需要添加的噪声较少。
2. RealGalaxy类具有一个noise属性，用于跟踪和传播噪声。
3. GAL SIM可以自动跟踪变换对噪声场的影响，并在最终图像中实现噪声均匀化。
4. 在处理包含多个星系的大图像时，GAL SIM通过单独处理每个星系的图像来管理噪声。
5. VariableGaussianNoise类可以为每个像素添加可变噪声，以实现整个图像的噪声均匀。
6. 包含用于估计星系形状加权矩和PSF校正剪切的例程。

关键要点：

1. Hirata & Seljak (2003)开发了一种新的PSF校正方法，称为“重新高斯化”。
2. 这些代码作为独立的C包发布，名为HSM，并作为开源代码公开。
3. FindAdaptiveMoments函数实现了“自适应矩”方法，用于计算最佳拟合椭圆高斯的矩。
4. EstimateShear函数实现多种方法进行PSF校正，包括分析PSF的峰度影响、线性方法、“重新高斯化”方法和KSB方法。
5. 这些方法应用于GAL SIM图像，以计算星系形状的“扭曲”，可用于估算整体的剪切。

关键要点：

1. GAL SIM提供了两种方式来调整形状测量算法的参数，包括通过HSMParams结构和特定函数参数。
2. GAL SIM的版本相比独立的C代码有多项改进，如更直观的用户界面、优化的卷积和傅里叶变换、以及修复了输入PSF图像非方形时的错误。
3. 数值验证部分强调了GAL SIM在透镜剪切和放大模拟中的图像变换精度。
4. 验证的准确性基于对渲染轮廓的大小和椭圆率的测量，使用自适应矩估计方法。

关键要点：

1. 定义了g1、g2和尺寸σ的误差公式，用于估计不同验证测试中的误差。
2. 为了符合Euclid项目的弱引力透镜测量要求，目标误差值为m i ≃ 2 × 10^-3和ci ≃ 2 × 10^-4。
3. 模拟需要满足更严格的条件，即误差达到Euclid要求的1/10（m x < 2 × 10^-4, cx < 2 × 10^-5），才能用于弱引力透镜剪切估计和其他精密宇宙学应用。
4. 通过比较自适应矩量测量的渲染方法来进行测试，表明渲染精确度可以通过更严格的参数设置实现改进。
5. GAL SIM的默认设置在速度和精度之间平衡，通常能满足1/10的Euclid要求，但不是所有情况下都如此。

1. 比较测试专注于图像渲染的差异，使用无噪声或极低噪声的图像进行测试，确保差异仅来自于图像渲染方法。

2. 从2013年7月到论文撰写时进行了GAL SIM软件的验证。期间，渲染对象的例程没有重大改变，除非为了满足验证标准。

3. DFT渲染和光子发射方法的等效性是测试渲染准确性的重要手段，两种方法需要在测量对象的尺寸和形状上给出等效结果。

4. Sérsic剖面的傅里叶方法渲染具有挑战性，特别是当参数n ≳ 3时，因其中心极为尖锐且边缘宽广，对参数选择是一个良好的测试。

- 研究构建了Sérsic指数在1.5到6.2范围内的天体模型，并使用与COSMOS星系匹配的分布来确定半光半径和内在椭圆率。
- 这些星系被随机旋转，并与COSMOS类似的PSF卷积，然后通过DFT和光子射击方法渲染成图像。
- 误差估计基于两种图像的自适应矩形形状和大小估计的差异。
- 每个星系模型进行了多次高信噪比的光子射击试验，以避免噪声偏差。
- 结果显示，形状和大小估计的差异符合m型偏差的容差要求，c型加性偏差在所有Sérsic指数下均与零一致。
- 研究还分析了GSParams参数对m x,DFT的影响，发现增加folding_threshold参数会降低渲染一致性，尤其影响对象大小的表示。
- 默认的GSParams参数在所有测试中表现出保守的良好性能。

关键要点：

1. 插值图像在傅里叶变换（DFT）渲染中存在特殊挑战，影响准确性因素包括傅里叶空间插值的选择和原始图像周围的填充量。
2. 为验证准确性，研究对6000个COSMOS星系拟合的Sérsic模型进行了测试。
3. 每个星系被建模为一个Sersic对象，并通过COSMOS样式的PSF卷积。结果被绘制为分辨率为0.03弧秒的图像，用于创建插值图像轮廓。
4. 样本中的每个对象都被建模为解析卷积和插值图像，并应用小剪切，使用DFT渲染算法绘制。
5. 每个轮廓通过小高斯卷积来强制使用DFT渲染方法。

1. 研究比较了使用光子射击和DFT渲染方法模拟的Sérsic轮廓的剪切和大小测量差异。
2. 结果显示，Sérsic指数为1.5和6.2的30个星系的测量值存在差异，尤其是高指数轮廓的低σ估计。
3. 图4展示了与Sérsic指数相关的渲染引起的椭圆度和大小差异的乘法斜率估计。
4. 图5分析了渲染参数folding_threshold对椭圆度和大小差异的影响，使用了270个COSMOS星系模型。
5. 目标是确保渲染误差不超过弱透镜精度要求的十分之一。

1. GAL-SIM模型的目标是保证误差不超过弱透镜精度需求的十分之一。
2. 自适应矩估计显示椭圆率变化在参数模型和插值图像之间的一致性优于Euclid需求的十分之一，这对所有高于双线性插值的实数和傅里叶空间插值都是一致的。
3. 对象大小的变化测试结果相似，验证了InterpolatedImage处理简单输入图像变换的能力。
4. 测试被扩展到更复杂的RealGalaxy轮廓，结果显示对象椭圆率的估计与已知的剪切一致。
5. 为验证剪切噪声处理能力，测试加入了额外的漂白噪声，使用了6000个COSMOS星系图像样本。
6. 不同插值参数设置下的测试，表明较大pad_factor值能提高准确性但增加计算时间。
7. 在所有测试中，设置pad_factor为4，并使用二维五次插值时，结果满足预期。

1. 在GAL SIM中选择默认值m i,interp< 2 × 10−4和ci,interp< 2 × 10−5是合理的，ci,interp的值很小。
2. 检查了剪切响应的渗漏，结果显示在测试的插值器中，渗漏在所需范围内，设置pad_factor为4和6时与零一致。
3. RealGalaxy测试未达标的情况是同时模拟两个剪切分量和放大，这导致mσ,interp∼ (4± 0.4)× 10−4，超出目标2× 10−4。
4. 放大在宇宙学上通常比剪切更容易受到噪声影响，此偏差在Stage IV调查数据中可能是可以接受的。
5. 为验证GAL SIM的高精度，成功测试了低分辨率观察条件下应用剪切的重卷算法。

关键要点：

- 输入参数包括一系列数值和一个名为pad_factor的参数。
- pad_factor的值范围从-0.0003到0.0003。
- 讨论了乘法斜率m 1,interp。
- k插值器用于描述∆g1相对于施加的g1的斜率。
- 使用的插值方法包括三次、五次、lanczos3、lanczos4、lanczos5和lanczos7。

关键要点：

1. 研究探讨了不同傅里叶空间插值方法（如三次、五次、Lanczos等）对乘法偏差的影响。
2. 通过调整填充因子，分析了在应用剪切和自适应矩估计之间的关系。
3. 使用Sérsic轮廓和已知的COSMOS样本PSF进行高分辨率图像渲染，并模拟真实COSMOS星系图像。
4. 通过重卷积过程评估有效剪切的误差，定义了相关的误差指标。
5. 测试使用了从COSMOS星系目录中选取的200个轮廓，并采用8倍环形测试配置进行随机旋转。
6. 目标是确保误差不超过弱透镜精度要求的十分之一，以满足Stage IV调查的标准。

关键要点：

1. 研究不仅要考虑平均值，还要调查m和c的范围，以识别方法在某些星系类型上可能失效的情况。
2. 图7显示了m i,reconv与folding_threshold参数的关系。在接近默认值时，整体平均满足精度要求。
3. 在200个COSMOS星系样本中，只有少数（3/200）未达到默认folding_threshold的要求，但不影响默认设置的使用。
4. 使用足够大的代表性星系模型训练集时，m i,reconv的变化不影响弱引力透镜模拟的准确性。
5. 如果需要更高精度，用户可以调整GSParams值，降低folding_threshold可满足所有测试星系的要求。
6. 加性偏差ci,reconv在所有情况下都极小且接近于零。
7. 结果表明，重卷积过程中的近似不会显著影响GAL SIM在弱引力透镜模拟中生成准确图像的能力。
8. 尽管默认设置在许多情况下的精度超过要求5-10倍，但不能保证适用于所有未来应用。用户需谨慎使用。
    
    关键要点：

> Finished chain.

> Finished chain.


> Entering new StuffDocumentsChain chain...


> Entering new LLMChain chain...
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    1. 用户应根据自身需求进行测试，特别是在已知数据特性时，需自行验证并调整渲染参数。
2. 所有测试采用了圆形PSF，但在某些情况下，可能会出现渲染问题。
3. 仅使用特定的COSMOS星系样本进行训练，其他样本可能不符合当前渲染要求。
4. 用户可能需要根据不同的输入和分析需求修改和完善测试。
5. GAL SIM注重渲染精度，同时也优化了代码以提高速度。

关键要点：

1. GAL SIM代码的性能优化主要通过在时间关键操作中使用C++实现，而Python仅作为用户界面。
2. 采用了C和C++常用的优化技术，如预计算、紧凑的内循环、迭代器、查找表和LRU缓存等。
3. 计算卷积的快速傅里叶变换（FFT）通常占用大部分计算时间，使用了FFTW包来加速。
4. 为了加快FFT计算，图像尺寸被调整为2的幂或3倍的2的幂。
5. 在速度和精度之间进行了权衡，只使用满足所需精度的最小FFT图像尺寸。

1. 对于径向对称的轮廓，可以将二维FFT转换为一维Hankel变换，从而提高DFT计算的效率。
2. 这种方法尤其适用于Sérsic分布的情况，因为它们具有较大的动态范围。
3. GAL SIM使用了一种高效的自适应Gauss-Kronrod-Patterson算法来执行Hankel变换和其他积分运算。
4. 尽管矩阵计算在总运行时间中占比不大，但通过使用TMV库和BLAS库来优化效率。
5. 为了进行傅里叶空间计算，需要对插值图像使用Lanczos插值进行有效的函数评估。

1. Sine Integral (Si(x)) Calculation: The existing formulae for computing Si(x) were not accurate enough, so new formulae were developed to achieve an accuracy of 10^-16.

2. Parallelization in GAL SIM: The software allows for easy parallel processing using a configuration file, which simplifies the use of multiple processes for users.

3. Rendering Timings in GAL SIM: The time to render images varies based on profile complexity and image scale. Analytic profiles typically render quickly (around 0.01 seconds per object), while models with interpolated images, like OpticalPSF or RealGalaxy, take longer (around 0.1 seconds per object).

关键要点：

1. 光子投射法与DFT渲染的执行时间不同，光子数在103-104范围内时，光子投射法更快，适合处理微弱天体。
2. 渲染速度可能受以下因素影响：
   - 去相关噪声的白化过程会增加渲染时间，尤其是在使用RealGalaxy时。
   - 使用非常小像素的DFT渲染会变慢，渲染时间与像素大小有关。
   - 随着Sérsic指数的变化，需要为每个不同的n值预计算积分，增加了时间成本。
   - 变动的光学PSF参数导致高昂的设置成本，当PSF不一致时，这项开销可能会显著影响速度。

1. 不同物体需要单独计算变量PSF，使其生成过程耗时。
2. 复杂的色度依赖性使图像生成变慢，简单的光谱能量分布和滤波器传递比复杂的更有效率。
3. GAL SIM已在未来版本中优化处理复杂色度对象。
4. 示例图像模拟LSST焦平面，每平方角分布有70个物体，包括20%星星和具有大气视力及光学组件的PSF。
5. 图像中包含多种真实数据特征，配置文件仅有122行，体现了GAL SIM配置模式的优势。

1. 在现代笔记本上，单个4K×4K芯片的渲染时间约为3分钟，使用8个核心同时运行时，整个视野（共189个芯片）可在一小时多一点的时间内完成渲染。

2. GAL SIM目前无法模拟真实图像的许多特征，如饱和、溢出、渐晕和宇宙射线等。

3. 尽管存在这些不足，简化的图像仍然对研究图像处理算法非常有用，例如用于研究混合效应、星系分离算法和剪切估计。

4. GAL SIM尚不能模拟许多光学和近红外天文观测中的物理效应，这些效应对未来星系调查数据的准确测量至关重要。

5. 物理大气PSF模型是GAL SIM目前缺乏的功能之一，尽管在GREAT3项目的准备工作中曾考虑过添加此功能。

关键要点：

1. 非线性探测器效应：GALSIM目前无法模拟像素饱和、串扰等效应，这些会影响图像的光通量和形状测定。
2. 图像伪影：如鬼影和探测器持久性，这些效应难以建模或去除，影响天文对象的测量。
3. 宇宙射线：在即将进行的第四阶段调查中，特别是空间任务中，模拟这些效应非常重要。
4. 近场污染：如卫星轨迹和流星，这些效应对地面成像有影响，目前GALSIM不支持。
5. 弯曲：弱引力弯曲的模拟与GALSIM的傅里叶空间渲染不兼容，目前未实现。
6. 渐晕、量子效率变化和平场效应：GALSIM未考虑光子检测效率的变化。

1. GAL SIM 是一个用于模拟银河系图像的模块化工具包，旨在为即将进行的深空成像调查提供高精度模拟。
2. 当前的功能包括处理输出图像中的位置变化和像素内的变化，但需要定制实现以处理复杂的天文坐标系统（WCS）功能。
3. 未来的改进可能包括扩展光学波前处理和支持 Shapelet 对象的光子射击。
4. 项目采用开放和协作的开发模式，期望在未来增加更多功能。

GAL SIM 是一个用于天文图像模拟的软件，支持多种世界坐标系统（WCS）下的天文对象描述和渲染。其创新技术包括光子射击和噪声美白，以及在多种 WCS 转换下的一致处理。GAL SIM 提供多种并行图像渲染方法，确保高精度输出，适用于如 Euclid、LSST 和 WFIRST-AFTA 等项目的弱引力透镜变换。用户可以通过调整输入参数和 GSParams 结构来平衡渲染精度和执行速度。软件的测试和验证是关键，用户需根据具体应用调整测试方案。

1. GAL SIM是一个用于模拟星系调查图像的开源工具包，尽管目前还不能模拟某些重要效应，但其开发和支持工作仍在持续进行。
2. GAL SIM已被用于GREAT3挑战，并在多项测试中证明了其高精度的渲染能力，可作为开发基准或代码比较的参考点。
3. 该工具包易于扩展，并可作为类库用于进一步的天文图像分析应用开发。
4. 项目得到了NASA、欧洲研究委员会和美国国家科学基金会等机构的支持。

1. 研究得到了多个机构的支持，包括NASA、Sloan Fellowship、日本学术振兴会、美国能源部和国家科学基金会。
2. 作者使用了UCL Legion高性能计算设施来完成这项工作。
3. GAL SIM透镜引擎使用离散有限网格来近似真实连续函数，涉及实空间和傅里叶空间的网格参数。
4. 采用了特定的傅里叶变换惯例来描述宇宙剪切和物质场的统计数据。

关键要点如下：

1. 文中采用角频率而非普通频率来表示傅里叶变换，引入了一些额外的 \(2\pi\) 因子。
2. 文中推导了傅里叶变换性质的表达，其中用到了非单位制、角频率惯例。
3. 阐述了泊松求和公式在离散傅里叶变换中近似连续函数的重要性，并指出在角频率惯例下公式中包含 \(2\pi\) 因子。
4. 提出了一种表示泊松求和公式的实用表达式，并引入了 \(\Delta k\) 作为简化变量。
5. 定义了一个无量纲函数 \(P_{\Delta k}[q,p]\)，该函数从功率谱中取样，并通过傅里叶逆变换与离散样本的乘积表现出特定的数学性质。
6. 使用狄拉克梳函数和卷积定理来表达这一结果。

这段内容介绍了一种用于分析周期性信号或函数的技术，通过对一个无限的、周期为 \(L = 2\pi/\Delta k\) 的相关函数进行研究。关键要点包括：

1. **周期性表示和采样**：函数 \(\xi_{2\pi/\Delta k}(\theta_1, \theta_2)\) 是一个无限周期性求和的表达式，可以通过取适当间隔的样本来了解函数的非重叠区域。

2. **离散傅里叶变换（DTFT）**：通过泊松求和公式，可以将函数表示为离散时间傅里叶逆变换。这表明所有有关 \(\xi^+(\theta_1, \theta_2)\) 的信息都包含在函数的一个周期内。

3. **数值分析中的离散化**：通过在每个维度上取 \(N\) 个等间距的样本，估算函数的离散值。这些样本在实空间中被间隔 \(\Delta \theta = 2\pi/\Delta kN\)。

4. **有限序列截断**：实际计算中需要截断 \(P_{\Delta k}\) 序列以使其长度有限，并通常取相同数量 \(N\) 的样本点用于实空间和傅里叶空间的计算。

总体而言，该内容涉及如何将连续信号通过采样和截断来实现离散化，以便进行数值分析。

1. 方程 (A.16) 描述了一个非单位逆离散傅里叶变换（DFT）。
2. NUMPY 的逆 DFT 通常定义中包含一个 1/N² 因子，用以保证 DFT 和逆 DFT 互为逆操作。
3. 快速傅里叶变换（FFT）算法可以高效计算 DFT。
4. 方程 (A.16) 用于在网格上构建一个高斯随机透镜场，其功率谱近似为 P(k)。
5. 在傅里叶空间中构建一个复杂的二维数组 κ̃[p, q]，并使用它生成傅里叶空间剪切场 g̃。
6. 通过逆 DFT 可以在实空间的网格上实现高斯透镜场 g[n, m]。

附录B. 高效评估正弦和余弦积分

定义正弦积分Si(x)和余弦积分Ci(x)。为了满足GAL SIM中涉及Lanczos插值的高效计算需求，我们开发了自有算法，用于准确计算Si(x)，更高效且精确。虽未在代码中使用Ci(x)，但出于完整性考虑，我们也提供了Ci(x)的计算方法。对于小参数，采用Padé近似展开式进行计算。使用Maple软件得到了精确至10^-16的公式适用于0≤x≤4。

关键要点：

1. 给出了两个辅助函数 \( f(x) \) 和 \( g(x) \) 的定义，用于计算三角积分。
2. \( f(x) \) 和 \( g(x) \) 的表达式涉及到对数积分函数 \( \text{Ci}(x) \) 和 \( \text{Si}(x) \)。
3. 当 \( x \to \infty \) 时，\( f(x) \) 和 \( g(x) \) 分别趋近于 \( 1/x \) 和 \( 1/x^2 \)。
4. 使用 Chebyshev-Padé 展开式来近似 \( f(x) \) 和 \( g(x) \)，在 \( x \geq 4 \) 的区间内精度优于 \( 10^{-16} \)。
5. 提供了 \( f(x) \) 和 \( g(x) \) 的具体展开式。

- 提供了一系列复杂的多项式表达式，这些表达式可以用于计算 Si(x) 函数，且可以达到双精度精度。
- 所有多项式使用 Horner’s 规则实现，使得计算有效。
- 提供了众多参考文献，涉及天文学和相关数学计算工具的研究。
    
    关键要点：

> Finished chain.

> Finished chain.


> Entering new StuffDocumentsChain chain...


> Entering new LLMChain chain...
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    这段内容列出了多篇学术论文的引用信息，涉及天文学、光学、统计学等领域的研究。关键要点包括：

1. 研究领域：主要涉及天文学、光学、统计学和相关技术。
2. 作者和年份：列出了多位作者及其发表论文的年份。
3. 期刊和会议：论文发表在不同的学术期刊和会议上，如PASP、AJ、MNRAS等。
4. 主题多样：涵盖了从光学原理到天文观测技术、统计方法等多方面的研究。

这些引用为相关领域的研究提供了重要的文献基础。

这段内容列出了多篇天文学和天体物理学领域的学术论文及其作者，涉及的主题包括宇宙学、引力透镜效应、望远镜校准等。主要作者包括Kacprzak、Kaiser、Kitching、Koekemoer、Lackner、Laureijs、Leauthaud、Long、Luppino、Mandelbaum、Massey、Melchior等。研究发表在《MNRAS》、《ApJ》、《ApJS》等期刊上，部分论文也在会议论文集中发表。

这段内容列出了多篇学术论文和技术报告的参考文献，涉及天文学、光学仪器、数值计算和宇宙学等领域。文献作者包括Meng、Meyers、Miyazaki、Moffat、Moore、Nakajima、Navarro、Noll、Patterson、Peacock、Pence、Plazas、Press、Racine、Rasmussen、Refregier、Reyes、Rhodes、Rolland和Rowe等。出版物涵盖了期刊文章、会议论文和技术报告，发表在《PASP》、《Journal of Instrumentation》、《A&A》、《MNRAS》等期刊上。

这段内容列出了多篇关于天文学和物理学的学术论文，涉及主题包括引力透镜、星系结构、宇宙学观测等。每篇论文的作者、发表年份、期刊名称和页码信息均被提及。
    
    关键要点：

> Finished chain.

> Finished chain.


> Entering new LLMChain chain...
Prompt after formatting:
请用简洁的语言总结以下内容：
    
    GALSIM是一个开源的星系图像模拟工具包，由国际科学家合作开发，旨在支持天文学研究中的高效图像模拟。它能够生成恒星和星系图像，支持高精度操作如卷积和渲染，适用于当前和未来的大型宇宙学调查。GALSIM特别关注弱引力透镜技术，通过模拟减少系统误差，帮助研究宇宙膨胀和物质结构。软件采用模块化设计，使用Python和C++编写，提供详细文档和示例，支持多种天文对象模型和图像处理功能。GALSIM还强调代码质量和跨平台兼容性，通过GitHub进行协作开发和代码审查。

关键要点：

1. 光学点扩散函数（PSF）复杂，需通过插值评估；InterpolatedImage类用于将图像数组转换为连续亮度分布。
2. 不同插值核在渲染中有不同的计算复杂度和适用性，高阶插值核提供性能和精度平衡。
3. GAL SIM支持对亮度分布进行变换，包括缩放、平移、旋转等，结合shift和transform可实现任意仿射变换。
4. GAL SIM可合并亮度轮廓，支持卷积、反卷积等操作，适用于模拟天文图像的PSF转换。
5. Chromatic类支持波长依赖的模拟，允许复杂星系形态的创建。
6. GAL SIM用于模拟弱引力透镜效应，支持剪切和会聚的生成与变换。
7. 支持宇宙学剪切场的模拟，提供工具评估网格选择对剪切相关函数的影响。
8. WCS处理支持简单像素比例和复杂函数，允许从天空坐标到图像坐标的转换。
9. 渲染方法包括直接绘制、DFT和光子射击，适用于不同对象和操作。
10. 处理PSF时需注意坐标系转换，避免重复卷积导致的误差。

1. Hankel变换在首次创建Kolmogorov对象时计算并保存，避免重复计算。
2. 径向对称性和向量化技术可加速计算，Shapelet函数使用递推关系渲染。
3. 不同渲染方法（实空间、傅里叶空间、光子射击）有各自的特性和复杂度。
4. 卷积和逆卷积处理方法各异，分析不同GAL SIM对象的特点及表示方式。
5. "LUT"是预计算并存储的积分函数，光子发射方法包括解析法和区间法。
6. 带限图像在傅里叶变换中有零值，选择合适的\( k_{\text{max}} \)来近似无界PSF。
7. DFT输出是周期函数的折叠结果，GAL SIM调整网格以减少误差。
8. 插值器影响图像范围，Sinc插值器扩展范围，Lanczos插值器更紧凑。
9. 光子射击技术用于模拟图像，支持非均匀权重和负亮度值。
10. 光子发射算法用于特定轮廓，插值图像需要网格点分配和累积概率。
11. 光子发射方法在低信噪比情况下更快，但处理负光子时需发射更多光子。

1. **光子流量和噪声处理**：每个光子携带流量±g，目标是使总流量和方差达到期望值f。计算假设η为常数，但实际情况导致光子图像间存在相关性。噪声模式类似真实光子图像，但不应依赖于噪声的稳定性。

2. **光子数量调整**：在中等高流量物体中，通过减少光子数量并增加每个光子的流量，可以实现相同的信噪比，节省计算成本。

3. **噪声模型和处理**：GAL SIM提供多种噪声模型，包括Poisson和高斯噪声。相关噪声在图像中常见，尤其在HST图像中。GAL SIM能模拟和处理这些噪声。

4. **噪声美白技术**：通过添加额外的漂白噪声，将相关噪声转换为不相关的白噪声，以减少模拟中的系统偏差。

5. **插值和卷积处理**：GAL SIM提供多种插值选项，并在噪声模型的卷积处理中采用双线性插值法，以提高计算效率。

6. **相关噪声的影响**：相关噪声影响弱透镜效应的剪切校准精度，需在高精度模拟中考虑。GAL SIM通过噪声美白技术处理相关噪声。

研究内容总结如下：

1. 在COSMOS F814W图像中对噪声进行了标准化处理，减少了噪声相关性，使用的方法使噪声几乎不可检测。
2. 噪声美白提高了图像方差但降低了信噪比，影响了对象属性的估计。
3. 噪声去色处理后信息损失与对象特性及原始噪声相关性有关，较大像素尺度和宽PSF卷积减少了噪声美白需求。
4. GAL SIM提供了图像噪声处理方法，包括whitenNoise和symmetrizeNoise，并具备实时跟踪噪声影响的功能。
5. Hirata & Seljak (2003)开发的PSF校正方法被用来改善星系形状估计，应用于GAL SIM中。
6. GAL SIM在形状测量的算法参数调整上提供了灵活性，强调其在图像变形精度上的优越性。
7. 软件被验证能满足Euclid项目的精度要求，通过测试渲染方法确保误差不超过标准所需的十分之一。
8. GAL SIM的插值方法在傅里叶变换中具有挑战性，但已进行测试保证其渲染精度。
9. 研究强调对星系模型的准确渲染，确保满足弱引力透镜模拟的精度要求，且可以通过参数调整进一步增强。

综上所述，研究从噪声处理、形状估计到渲染精度验证，全面探讨了提高图像质量和测量准确性的手段。

1. **用户自定义与测试**：用户需根据自身需求和数据特性调整渲染参数，并验证测试结果。

2. **性能优化**：GAL SIM通过C++实现关键操作，使用FFT加速卷积计算，并在速度与精度间进行权衡。

3. **渲染与并行处理**：支持多种渲染方法和并行处理，适用于复杂的天文图像模拟。

4. **功能与限制**：尽管GAL SIM无法模拟某些效应，如饱和和宇宙射线，但其高精度渲染对算法研究有用。

5. **开发与支持**：项目持续开发，支持扩展功能，得到多个机构的支持。

6. **数学与算法**：使用傅里叶变换和自有算法提高计算效率，特别是在正弦积分计算中。

这段内容总结了多篇学术论文的引用信息，主要涉及天文学、光学、统计学和相关技术领域。关键要点包括：

1. 涉及领域：研究领域涵盖天文学、光学、统计学、数值计算和宇宙学。
2. 作者和年份：列出多位作者及其发表年份，如Kacprzak、Kaiser、Meng、Meyers等。
3. 期刊和会议：论文发表在《MNRAS》、《ApJ》、《PASP》、《Journal of Instrumentation》等期刊和会议上。
4. 研究主题：涵盖宇宙学、引力透镜效应、望远镜校准、光学仪器等多样的主题。

这些论文为相关领域的研究提供了重要的文献基础。
    
    关键要点：

> Finished chain.

> Finished chain.

生成的知识库内容：
 GALSIM是一个开源的星系图像模拟工具，支持高效图像模拟，特别关注弱引力透镜技术。它采用模块化设计，使用Python和C++编写，支持多种天文对象模型和图像处理功能。关键要点包括：

1. 支持复杂PSF的插值评估和高精度图像变换。
2. 提供卷积、反卷积和波长依赖的模拟功能。
3. 支持宇宙学剪切场模拟和WCS处理。
4. 提供多种渲染方法和噪声处理技术。
5. 强调代码质量、跨平台兼容性和用户自定义。
6. 通过GitHub进行协作开发，持续优化性能。
7. 研究噪声处理、形状估计和渲染精度，确保图像质量和测量准确性。
8. 支持多种渲染方法和并行处理，适用于复杂天文图像模拟。
---------- user ----------
请根据文档说明项目使用的主要技术方法。
---------- project_assistant ----------
[MemoryContent(content='GALSIM是一个开源的星系图像模拟工具，支持高效图像模拟，特别关注弱引力透镜技术。它采用模块化设计，使用Python和C++编写，支持多种天文对象模型和图像处理功能。关键要点包括：\n\n1. 支持复杂PSF的插值评估和高精度图像变换。\n2. 提供卷积、反卷积和波长依赖的模拟功能。\n3. 支持宇宙学剪切场模拟和WCS处理。\n4. 提供多种渲染方法和噪声处理技术。\n5. 强调代码质量、跨平台兼容性和用户自定义。\n6. 通过GitHub进行协作开发，持续优化性能。\n7. 研究噪声处理、形状估计和渲染精度，确保图像质量和测量准确性。\n8. 支持多种渲染方法和并行处理，适用于复杂天文图像模拟。', mime_type=<MemoryMimeType.TEXT: 'text/plain'>, metadata=None)]
---------- project_assistant ----------
项目使用的主要技术方法包括：

1. **模块化设计**：使用Python和C++编写，便于扩展和自定义。
2. **复杂PSF的插值评估**：支撑高精度图像变换。
3. **卷积与反卷积、波长依赖的模拟**：提升模拟的细节和准确性。
4. **宇宙学剪切场模拟与WCS处理**：支持广泛的天文学应用。
5. **多种渲染方法与噪声处理**：提升图像质量和测量的准确性。
6. **并行处理与跨平台兼容**：提高计算效率，适应不同系统环境。
7. **用户自定义与协作开发**：通过GitHub促进社区的参与和代码质量的优化。


memory 和 rag tools都需要（前者提取摘要，后者存放原信息）；
摘要的prompt需要优化，写一些大模型读论文的基本摘要框架即可。