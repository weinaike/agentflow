
from AgentFlow.tools.abstract_syntax_tree import AST
from AgentFlow.tools.utils import calculate_degrees, draw_flow_graph
from AgentFlow.tools.code_tool import query_important_functions, query_right_name
import json


if __name__ == "__main__":
    #src = '/home/jiangbo/GalSim/tmp/no_tpl'  # Change this to the path of your source code directory
    #include = ['/home/jiangbo/GalSim/tmp/no_tpl']  # Change this to the path of your include directory
    #test_clang_includes()

    configs = [ 
        {
            "src": "/home/jiangbo/GalSim/src",
            "include": ["/home/jiangbo/GalSim/include", "/home/jiangbo/GalSim/include/galsim", "/home/jiangbo/GalSim/src",  "/home/jiangbo/GalSim/src/cuda_kernels", "/home/jiangbo/GalSim/downloaded_eigen/eigen-3.4.0"],
            #"scope": "galsim::SBSpergel::SBSpergelImpl",
            "scope": "galsim::SBVonKarman::SBVonKarmanImpl",
            "method": "shoot",
            "namespaces": [],
            "cache_dir": "/home/jiangbo/agentflow/workspace/galsim/cache_dir",
            "use_cache": True,
            "output_filters": [
                lambda cursor: not cursor.location.file.name.startswith("/home/jiangbo/GalSim/"),
                #lambda cursor: not CursorUtils.get_namespace(cursor) == "galsim"
            ]
        }
        ,{
            "src": "/home/jiangbo/arctic/arctic/src",
            "include": ["/home/jiangbo/arctic/arctic/include", "/home/jiangbo/arctic/gsl-2.7.1"],

            "scope": "",
            "method": "add_cti",

            #"scope": "",
            #"method": "clock_charge_in_one_direction",

            #"scope": "TrapManagerInstantCapture",
            #"method": "n_electrons_released",

            "namespaces": [],
            "cache_dir": "/home/jiangbo/AutoCoder/cached_ast_dir/arctic",
            "use_cache": True,
            "output_filters": [
                lambda cursor: not cursor.location.file.name.startswith("/home/jiangbo/arctic/arctic")
            ]
        }
    ]

    config = configs[-2]

    src = config["src"]
    include = config["include"]
    namespaces = config["namespaces"]
    cache_dir = config["cache_dir"]
    use_cache = config["use_cache"]
    # output_filters = config["output_filters"]
    method = config["method"]
    scope = config["scope"]

    ast = AST()

    ast.create_cache(src_dir=src, include_dir=include, namespaces=namespaces, parsing_filters=[], cache_file=cache_dir, load=use_cache)
    dir_list = [ast.directory]
    dir_list.extend(ast.include)

    output_filters =  [
        lambda cursor: all(not cursor.location.file.name.startswith(directory) for directory in list(set(dir_list))),
    ]




    names = ["galsim::PhotonArray::addTo","galsim::PhotonArray::convolve","galsim::PhotonArray::size","galsim::PhotonArray::convolveShuffle","galsim::SBProfile::shoot","galsim::SBVonKarman::shoot","galsim::SBConvolve::shoot","galsim::SBAutoConvolve::shoot","galsim::SBAutoCorrelate::shoot","galsim::SBInterpolatedImage::shoot","galsim::SBInterpolatedKImage::shoot","galsim::SBAiry::shoot","galsim::SBExponential::shoot","galsim::SBSersic::shoot","galsim::SBInclinedSersic::shoot","galsim::SBDeconvolve::shoot","galsim::SBKolmogorov::shoot","galsim::SBDeltaFunction::shoot","galsim::SBAdd::shoot","galsim::SBFourierSqrt::shoot","galsim::SBShapelet::shoot","galsim::SBSpergel::shoot","galsim::SBGaussian::shoot","galsim::SBMoffat::shoot","galsim::SBSecondKick::shoot","galsim::SBInclinedExponential::shoot","galsim::SBBox::shoot","galsim::SBTopHat::shoot","galsim::BaseDeviate::generate","galsim::BaseDeviate::operator()","galsim::BaseDeviate::BaseDeviate","galsim::UniformDeviate::UniformDeviate","galsim::UniformDeviate::generate","galsim::GaussianDeviate::generate","galsim::BinomialDeviate::generate","galsim::PoissonDeviate::generate","galsim::WeibullDeviate::generate","galsim::GammaDeviate::generate","galsim::Chi2Deviate::generate","boost::random::uniform_real_distribution::uniform_real_distribution","galsim::BaseDeviate::generate1","galsim::Bounds::write","galsim::operator<<","galsim::PhotonArray::addTo::target","galsim::Bounds::isDefined"]
    right_name = query_right_name(names)

    functions = [
    "galsim::PhotonArray::addTo",
    "galsim::PhotonArray::convolve",
    "galsim::SBProfile::shoot",
    "galsim::SBVonKarman::SBVonKarmanImpl::shoot",
    "galsim::SBConvolve::SBConvolveImpl::shoot",
    "galsim::SBAutoConvolve::SBAutoConvolveImpl::shoot",
    "galsim::SBAutoCorrelate::SBAutoCorrelateImpl::shoot",
    "galsim::SBInterpolatedImage::SBInterpolatedImageImpl::shoot",
    "galsim::SBInterpolatedKImage::SBInterpolatedKImageImpl::shoot",
    "galsim::SBAiry::SBAiryImpl::shoot",
    "galsim::SBExponential::SBExponentialImpl::shoot",
    "galsim::SBSersic::SBSersicImpl::shoot",
    "galsim::SBInclinedSersic::SBInclinedSersicImpl::shoot",
    "galsim::SBDeconvolve::SBDeconvolveImpl::shoot",
    "galsim::SBKolmogorov::SBKolmogorovImpl::shoot",
    "galsim::SBDeltaFunction::SBDeltaFunctionImpl::shoot",
    "galsim::SBAdd::SBAddImpl::shoot",
    "galsim::SBFourierSqrt::SBFourierSqrtImpl::shoot",
    "galsim::SBShapelet::SBShapeletImpl::shoot",
    "galsim::SBSpergel::SBSpergelImpl::shoot",
    "galsim::SBGaussian::SBGaussianImpl::shoot",
    "galsim::SBMoffat::SBMoffatImpl::shoot",
    "galsim::SBSecondKick::SBSecondKickImpl::shoot",
    "galsim::SBInclinedExponential::SBInclinedExponentialImpl::shoot",
    "galsim::SBBox::SBBoxImpl::shoot",
    "galsim::SBTopHat::SBTopHatImpl::shoot",
    "galsim::BaseDeviate::generate"
    ]

    print(query_important_functions(functions))

    callgraphs = []
    for function in functions:
        method = function.split("::")[-1]
        scope = "::".join(function.split("::")[:-1])
        callgraph = ast.get_call_graph(method, scope, filters=output_filters)
        callgraphs.append(callgraph)

    merge_callgraph = {}
    for callgraph in callgraphs:
        merge_callgraph.update(callgraph.to_dict())

   
    

    draw_flow_graph(merge_callgraph)
    # print(json.dumps(filter_merge_callgraph, indent=4, ensure_ascii=False))
    degree = calculate_degrees(merge_callgraph)
    # 按first + second的值排序
    degree = dict(sorted(degree.items(), key=lambda x:  (x[1][0] + 1) * (x[1][1] - 1) , reverse=True))

    with open("degree.json", "w") as f:
        f.write(json.dumps(degree, indent=4, ensure_ascii=False))


    new_dict = {}
    for k, v in merge_callgraph.items():
        new_dict[k.replace("::", "_")]  = []
        for x in v:
            new_dict[k.replace("::", "_")].append(x.replace("::", "_"))
    # merge_callgraph.draw_callgraph()
    #code_snippets = ast.fetch_source_code(scope, method, type=None, filters=output_filters)
    #print(code_snippets)
    #print(ast.find_definition(method, class_name=None))
    # print(json.dumps(ast.find_declaration(method, class_name=None)))

    